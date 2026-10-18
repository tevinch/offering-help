terraform {
  required_version = ">= 1.15.0, < 2.0.0"

  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "3.3.0"
    }
  }
}

provider "helm" {}

locals {
  values_file = "${path.module}/values.yaml"
}

data "helm_template" "example" {
  name     = "values-file-example"
  chart    = "${path.module}/chart"
  validate = false

  values = [
    file(local.values_file),
    yamlencode({ rawValuesContent = file(local.values_file) }),
  ]

  lifecycle {
    precondition {
      condition     = base64encode(file(local.values_file)) == filebase64(local.values_file)
      error_message = "The values file changes under Terraform's Unicode normalization. This example cannot preserve its exact bytes."
    }
  }
}

output "rendered_values" {
  value = yamldecode(data.helm_template.example.manifest).data
}
