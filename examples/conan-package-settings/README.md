# Read Conan package settings and options

Keep your existing `ConanAPI.list.select()` query and read configuration at the **package ID** level. In Conan 2.33.0, `items()` and `package_dict(pref)` expose the **package revision** dictionary, which contains the timestamp in this case.

```python
from conan.api.conan_api import ConanAPI
from conan.api.model import ListPattern

api = ConanAPI()
selected = api.list.select(
    ListPattern("qt/*:*"),
    package_query="os=Android",
)

for recipe, references in selected.items():
    packages = selected.recipe_dict(recipe)["packages"]
    for reference in references:
        info = packages[reference.package_id]["info"]
        print(reference)
        print("settings:", info.get("settings", {}))
        print("options:", info.get("options", {}))
```

`recipe_dict()` is a public API. This uses configuration already returned by `select()`; it does not need a second query, private attributes or direct cache-file parsing.

The relevant structure returned by `serialize()` is:

```text
recipe name/version
└── revisions
    └── recipe revision
        └── packages
            └── package ID
                ├── info
                │   ├── settings
                │   └── options
                └── revisions
                    └── package revision
                        └── timestamp
```

`info` is the recorded package-ID configuration, shared by its revision entries in this result. It is not a list of every setting or option that the recipe supports, or an independent configuration history for each package revision. The `items()` documentation's settings/options example is misleading for this version: its values are the revision dictionaries.

## Run the example

Requires Python 3.8 or newer. The tests below were run with Python 3.10 and Conan 2.33.0.

```sh
python -m venv .venv
# macOS/Linux:
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python package_settings.py 'qt/*:*' --query 'os=Android'
```

The script prints JSON with each selected reference, settings and options, using Conan's normally configured local cache. Quote patterns so the shell does not expand `*`. Use a binary pattern such as `qt/*:*`; patterns with explicit `#*` can select multiple revisions. An empty package filter produces `[]`.

You can also inspect the complete structure with `selected.serialize()`, or use Conan's existing command:

```sh
conan list 'qt/*:*#*' -p 'os=Android' --format=json
```

The command requests all package revisions, so it may list more references than the Python example, which uses the latest revisions by default.

## Verify

```sh
python -m unittest -v
```

The two tests create a temporary Conan cache and a small local recipe, with no compiler, external packages or remote access. They export two Android packages with different option values and one Linux control, then check:

- The Android query returns both actual settings/options and excludes Linux.
- The result agrees with real `conan list --format=json` output.
- The script works end to end, repeated reads preserve the selected result, and a Windows filter returns no packages.

Reading the revision dictionary instead of package-ID `info` failed the configuration check before the working example was applied. Validation used synthetic local packages, not a Qt build or an existing user's cache.

References: [Conan list models](https://docs.conan.io/2/reference/extensions/python_api/model/list.html), [Conan 2.33.0 list implementation](https://github.com/conan-io/conan/blob/2.33.0/conan/api/model/list.py), and the [original usage question](https://github.com/conan-io/conan/issues/20430).

MIT licensed; see [LICENSE](LICENSE).

## Optional coffee

The example is free. If it helps and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
