# Per-stack inputs with Terramate

Create several stacks from one shared generator, with a different region, account and environment in each stack.

The inputs must exist when **generation** runs. They do not have to exist before `terramate create --no-generate`: that command creates the stack metadata without running the generator. Write each stack's `globals.tm.hcl` next, then run `terramate generate`.

This example was checked with Terramate **0.17.3**. It generates local `settings.json` files containing demonstration values. It does not run Terraform or deploy resources. You need Terramate and Git; the separate verifier also needs Python 3.

## One generator, three stacks

The two files in `template/` go at the root of a Terramate project. The shared generator reads each stack's inherited globals and its native stack name:

```hcl
generate_file "settings.json" {
  content = tm_jsonencode({
    stack       = terramate.stack.name
    region      = global.region
    account     = global.account
    environment = global.environment
  })
}
```

From this example's directory, run the following in a shell. It creates a separate temporary project and prints its location at the end.

```sh
(
  set -eu
  work_dir="$(mktemp -d)"
  cp template/*.tm.hcl "$work_dir/"
  cd "$work_dir"
  git -c init.templateDir= init --quiet

  terramate create --no-generate stacks/dev-eu
  terramate create --no-generate stacks/staging-us
  terramate create --no-generate stacks/prod-apac

  cat > stacks/dev-eu/globals.tm.hcl <<'HCL'
globals {
  region      = "eu-west-1"
  account     = "demo-development"
  environment = "development"
}
HCL
  cat > stacks/staging-us/globals.tm.hcl <<'HCL'
globals {
  region      = "us-east-1"
  account     = "demo-staging"
  environment = "staging"
}
HCL
  cat > stacks/prod-apac/globals.tm.hcl <<'HCL'
globals {
  region      = "ap-southeast-2"
  account     = "demo-production"
  environment = "production"
}
HCL

  terramate generate
  terramate list
  printf 'Example directory: %s\n' "$work_dir"
)
```

Each stack now has native `stack.tm.hcl` metadata, its own input file and its generated output. The generated file contents are:

`stacks/dev-eu/settings.json`

```json
{"account":"demo-development","environment":"development","region":"eu-west-1","stack":"dev-eu"}
```

`stacks/staging-us/settings.json`

```json
{"account":"demo-staging","environment":"staging","region":"us-east-1","stack":"staging-us"}
```

`stacks/prod-apac/settings.json`

```json
{"account":"demo-production","environment":"production","region":"ap-southeast-2","stack":"prod-apac"}
```

Change a value in a stack's `globals.tm.hcl` and run `terramate generate` again. The generator owns `settings.json`; put persistent edits in the input file or the shared generator.

Without `--no-generate`, ordinary `terramate create` also attempts generation. With the required globals missing, that attempt fails and can leave the newly created `stack.tm.hcl` behind. Supply the globals and run `terramate generate` to finish that stack rather than blindly repeating its creation.

## Alternative: inherited defaults before creation

If stacks can start with shared values, put those values in a parent `globals.tm.hcl` before normal creation. A stack inherits them; a stack-local definition can override one value.

This second example creates another temporary project. It uses normal `create`, which generates both outputs during creation.

```sh
(
  set -eu
  defaults_dir="$(mktemp -d)"
  cp template/*.tm.hcl "$defaults_dir/"
  cd "$defaults_dir"
  git -c init.templateDir= init --quiet

  cat > globals.tm.hcl <<'HCL'
globals {
  region      = "eu-central-1"
  account     = "demo-shared"
  environment = "preview"
}
HCL
  terramate create stacks/defaults

  mkdir -p stacks/override
  cat > stacks/override/globals.tm.hcl <<'HCL'
globals {
  region = "us-west-2"
}
HCL
  terramate create stacks/override
  printf 'Defaults example directory: %s\n' "$defaults_dir"
)
```

The first output contains `eu-central-1`, `demo-shared` and `preview`. The override output contains `us-west-2` while inheriting the same account and environment. If all three values differ for every stack, the first sequence keeps that input timing explicit.

These are **Terramate globals**, accessed as `global.region`, for example. Terraform `locals` are separate and do not provide these generator inputs. This example uses existing native commands; it adds no interactive input flag or template command.

## Verify locally

From this example's directory:

```sh
python3 verify.py --terramate "$(command -v terramate)"
```

Add `--report /path/to/report.json` to save the command results and observations. The verifier creates and removes fresh temporary Git projects, disables CLI telemetry and update checks in its own temporary configuration, and does not use cloud credentials or run infrastructure commands.

On 0.17.3 it passes **37 checks** over **17 Terramate invocations**. It checks all three exact outputs, native stack UUIDs and listing, repeated generation, changing just one stack, preservation of existing notes and metadata, missing-input diagnostics, and inherited defaults with a local override. It also confirms that omitting `--no-generate` fails before required inputs exist, and that omitting the generator fails the final-file acceptance even when `generate` exits successfully. The printed results include the final JSON objects; the edit check changes only staging's region to `us-west-2`.

The checks exercise the local CLI. They do not establish behavior for other Terramate releases, remote templates or an existing project's generators. Copy the small generator into a project only after choosing an output filename that it can own.

References: [create options](https://terramate.io/docs/cli/reference/cmdline/create/), [globals and inheritance](https://terramate.io/docs/cli/reference/variables/globals/), [file generation](https://terramate.io/docs/cli/code-generation/generate-file/).

## License

Copyright (c) 2026 Tevinch. MIT License.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Optional coffee

This example is free. If it saved you time, an entirely optional coffee contribution is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
