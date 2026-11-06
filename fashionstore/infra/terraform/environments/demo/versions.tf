terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Partial configuration: values come from backend.hcl
  #   terraform init -backend-config=backend.hcl
  backend "s3" {}
}
