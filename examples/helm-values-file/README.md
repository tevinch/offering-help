# Pass one values file as both YAML and text

Some Helm charts need the same file twice: once as ordinary chart values and once as a string such as `rawValuesContent`. In Terraform, pass two YAML documents to `values`:

```hcl
locals {
  values_file = "${path.module}/values.yaml"
}

resource "helm_release" "example" {
  name  = "example"
  chart = "./your-chart"

  values = [
    file(local.values_file),
    yamlencode({ rawValuesContent = file(local.values_file) }),
  ]

  lifecycle {
    precondition {
      condition     = base64encode(file(local.values_file)) == filebase64(local.values_file)
      error_message = "The values file changes under Terraform's Unicode normalization. Its exact bytes cannot be preserved."
    }
  }
}
```

Keep your existing Helm provider connection and chart settings. Move these two `values` entries into your existing release; the resource above only shows the relevant fields.

The first entry supplies the parsed values. The second supplies the original file as a YAML string. It represents the value assigned by `--set-file rawValuesContent=values.yaml`, without putting multiline file contents through `set` string parsing. Keep the second entry last so it overrides a same-named value in the file.

Use `file(...)` for the string, rather than decoding and re-encoding its contents: the chart can then receive the original comments, punctuation, and trailing newline. Use the same key path as the chart's working CLI command. A different subchart-specific key needs a matching nested object in the second entry.

## Try the local example

Install [Terraform](https://developer.hashicorp.com/terraform/install), then run from this directory:

```sh
terraform init
terraform plan
```

`main.tf` pins the Helm provider to `3.3.0` and uses [`helm_template`](https://registry.terraform.io/providers/hashicorp/helm/3.3.0/docs/data-sources/template) with `validate = false`. It renders the included local chart. It does not install a release or require a Kubernetes connection. The output contains parsed sample values and a base64 representation of the original file, making exact text preservation easy to check.

For the complete check, with Python 3 available:

```sh
python3 verify.py
```

The check removes the string entry to confirm that the chart rejects it, restores both entries, checks the rendered values and original file bytes, repeats the rendering, and confirms that source files stayed unchanged. It also tries a decomposed Unicode input and checks that the precondition rejects it. It works in a temporary directory and only runs `init`, `plan`, and `show`.

This example tests the local rendering contract with provider `3.3.0`. It does not test your vendor's private chart, cluster, or authentication. The original question used provider `2.8`; its `values` list also merges YAML documents, but this example does not claim to have run that older provider. [`file`](https://developer.hashicorp.com/terraform/language/functions/file) expects an existing UTF-8 text file. Terraform [normalizes Unicode strings](https://developer.hashicorp.com/terraform/language/functions/base64encode); the precondition rejects a file if that would change its bytes. This does not add binary-file support. Values and outputs can be stored in Terraform plans and state, so use the included nonsecret sample when trying the example.

## Optional coffee

If this saved you time, a coffee is welcome and entirely optional. The example is free to use.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
