"""Exercise the example against a real, disposable Conan cache."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

from conan.api.conan_api import ConanAPI
from conan.api.model import ListPattern

from package_settings import package_settings


class PackageSettingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.home = cls.root / "cache"
        cls.env = {**os.environ, "CONAN_HOME": str(cls.home)}
        cls.conan = str(Path(sys.executable).with_name("conan"))
        cls.recipe = cls.root / "recipe"
        cls.recipe.mkdir()
        (cls.recipe / "conanfile.py").write_text(textwrap.dedent('''\
            import os
            from conan import ConanFile
            from conan.tools.files import save

            class Sample(ConanFile):
                name = "sample"
                version = "1.0"
                settings = "os"
                options = {"flavor": ["plain", "extra"]}
                default_options = {"flavor": "plain"}

                def package(self):
                    save(self, os.path.join(self.package_folder, "marker.txt"),
                         str(self.settings.os) + ":" + str(self.options.flavor))
        '''), encoding="utf-8")
        profile = cls.root / "profile"
        profile.write_text("[settings]\nos=Linux\n", encoding="utf-8")
        for target, flavor in [("Android", "plain"), ("Android", "extra"), ("Linux", "plain")]:
            extra = ["-s:h", "os.api_level=24"] if target == "Android" else []
            cls.command("export-pkg", str(cls.recipe), "-pr:h", str(profile),
                        "-pr:b", str(profile), "-s:h", f"os={target}",
                        "-o:h", f"*:flavor={flavor}", "--no-remote", *extra)
        cls.api = ConanAPI(cache_folder=str(cls.home))

    @classmethod
    def command(cls, *args):
        result = subprocess.run([cls.conan, *args], cwd=cls.root, env=cls.env,
                                capture_output=True, text=True, check=True)
        return result.stdout

    def selected(self, query="os=Android"):
        return self.api.list.select(ListPattern("sample/*:*"), package_query=query)

    def test_filtered_settings_and_options_are_real_package_configuration(self):
        # Reading revision metadata instead of package-ID info loses both fields.
        selected = self.selected()
        before = copy.deepcopy(selected.serialize())
        rows = list(package_settings(selected))
        self.assertEqual(len(rows), 2)
        self.assertEqual(sorted((r.get("settings", {}).get("os"),
                                 r.get("options", {}).get("flavor")) for r in rows),
                         [("Android", "extra"), ("Android", "plain")])
        self.assertEqual(len({r["reference"] for r in rows}), 2)
        self.assertTrue(all("sample/1.0#" in r["reference"] for r in rows))
        self.assertEqual(list(package_settings(selected)), rows)
        self.assertEqual(selected.serialize(), before)

        # Compare the consumer's result to Conan's actual independent CLI output.
        cli = json.loads(self.command("list", "sample/*:*#*", "-p", "os=Android",
                                      "--format=json"))["Local Cache"]
        expected = []
        for recipe, body in cli.items():
            for revision, recipe_info in body["revisions"].items():
                for package_id, package in recipe_info["packages"].items():
                    for package_revision in package["revisions"]:
                        expected.append({
                            "reference": f"{recipe}#{revision}:{package_id}#{package_revision}",
                            "settings": package["info"].get("settings", {}),
                            "options": package["info"].get("options", {}),
                        })
        self.assertEqual(sorted(rows, key=lambda r: r["reference"]),
                         sorted(expected, key=lambda r: r["reference"]))
        rows[0]["settings"]["os"] = "Windows"
        rows[0]["options"]["flavor"] = "changed"
        self.assertEqual(selected.serialize(), before)
        self.assertEqual(sorted(package_settings(selected), key=lambda r: r["reference"]),
                         sorted(expected, key=lambda r: r["reference"]))

    def test_command_line_and_empty_filter(self):
        # A lost package query would leak the Linux control or produce nonempty output.
        script = Path(__file__).with_name("package_settings.py")
        result = subprocess.run([sys.executable, str(script), "sample/*:*", "--query", "os=Android"],
                                cwd=self.root, env=self.env, capture_output=True,
                                text=True, check=True)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["settings"]["os"] for row in rows}, {"Android"})
        self.assertEqual(list(package_settings(self.selected("os=Windows"))), [])


if __name__ == "__main__":
    unittest.main()
