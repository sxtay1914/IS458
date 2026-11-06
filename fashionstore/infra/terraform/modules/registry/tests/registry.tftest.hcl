mock_provider "aws" {
  source = "../../tests/mocks"
}

variables {
  name = "fs-test"
}

run "keeps_last_five_images" {
  assert {
    condition     = jsondecode(aws_ecr_lifecycle_policy.this["store-api"].policy).rules[0].selection.countNumber == 5
    error_message = "ECR keeps the last 5 images"
  }
  assert {
    condition     = aws_ecr_repository.this["store-api"].image_tag_mutability == "IMMUTABLE"
    error_message = "Tags are immutable"
  }
}
