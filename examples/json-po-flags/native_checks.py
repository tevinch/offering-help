"""Exercise Weblate's real PO reader and selected checks without a server/DB."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

from django.conf import settings


def inspect_po(path, translations=None, output=None):
    with tempfile.TemporaryDirectory(prefix="translation-check-") as data_dir:
        settings.configure(
            INSTALLED_APPS=["weblate.lang", "weblate.checks"], USE_I18N=False,
            CHECK_LIST=["weblate.checks.markup.MarkdownSyntaxCheck", "weblate.checks.format.JavaMessageFormatCheck"],
            AUTOFIX_LIST=[], DATA_DIR=data_dir, SITE_DOMAIN="localhost", ENABLE_HTTPS=False,
        )
        import django
        django.setup()
        from weblate.formats.ttkit import PoFormat
        from weblate.checks.models import CHECKS
        from weblate.utils.state import STATE_TRANSLATED
        destination = Path(path)
        if output:
            destination = Path(output)
            with Path(path).open("rb") as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target)
        store = PoFormat(destination, repo_temp_dir=data_dir)
        if translations is not None:
            known = {unit.context for unit in store.all_units}
            if not set(translations).issubset(known):
                raise ValueError("unknown translation context")
            for unit in store.all_units:
                if unit.context in translations:
                    unit.set_target(translations[unit.context])
                    unit.set_state(STATE_TRANSLATED)
        if output:
            store.save()
            store = PoFormat(destination, repo_temp_dir=data_dir)
        records = []
        for wrapped in store.all_units:
            if not wrapped.source:
                continue
            flags = wrapped.flags
            checks = []
            for name, checker in CHECKS.items():
                # These pure checks need a small unit context, not a database Unit.
                context = SimpleNamespace(
                    all_flags=flags, readonly=False, state=STATE_TRANSLATED, check_cache={},
                    effective_source=wrapped.source,
                    has_multiple_values=lambda sources, targets: False,
                    translation=SimpleNamespace(component=SimpleNamespace(file_format="po")),
                )
                calls = 0
                code = checker.check_target_unit.__func__.__code__
                def observe(frame, event, arg):
                    nonlocal calls
                    if event == "call" and frame.f_code is code and frame.f_locals.get("self") is checker:
                        calls += 1
                previous = sys.getprofile()
                sys.setprofile(observe)
                try:
                    failed = checker.check_target_with_flags([wrapped.source], [wrapped.target], context, flags)
                finally:
                    sys.setprofile(previous)
                checks.append({"id":name, "executions":calls, "failed":bool(failed)})
            records.append({"id":wrapped.context, "source":wrapped.source,
                            "target":wrapped.target, "description":wrapped.notes,
                            "flags":str(flags), "checks":checks})
        return {"resavedByWeblate": bool(output), "records": records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("po")
    parser.add_argument("--translations")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.translations and not args.output:
        parser.error("--translations requires a new --output PO path")
    translated = json.loads(Path(args.translations).read_text()) if args.translations else None
    print(json.dumps(inspect_po(args.po, translated, args.output), ensure_ascii=False))
