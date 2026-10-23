"""Read package configuration from a Conan package list."""

import argparse
import json

from conan.api.conan_api import ConanAPI
from conan.api.model import ListPattern


def package_settings(package_list):
    """Yield settings/options for each package revision selected by Conan."""
    for recipe, packages in package_list.items():
        package_ids = package_list.recipe_dict(recipe)["packages"]
        for reference in packages:
            info = package_ids[reference.package_id]["info"]
            yield {
                "reference": reference.repr_notime(),
                "settings": dict(info.get("settings", {})),
                "options": dict(info.get("options", {})),
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pattern", help="Conan binary pattern, for example 'qt/*:*'")
    parser.add_argument("--query", default=None, help="Package query, for example 'os=Android'")
    args = parser.parse_args()
    api = ConanAPI()
    selected = api.list.select(ListPattern(args.pattern), package_query=args.query)
    print(json.dumps(list(package_settings(selected)), indent=2))


if __name__ == "__main__":
    main()
