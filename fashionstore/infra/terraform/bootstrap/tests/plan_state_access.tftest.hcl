mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_data "aws_partition" {
    defaults = {
      partition = "aws"
    }
  }

  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }

  mock_resource "aws_iam_policy" {
    defaults = {
      arn = "arn:aws:iam::123456789012:policy/mock"
    }
  }
}

variables {
  github_repository   = "my-team/fashionstore"
  budget_alert_emails = ["lead@example.com"]
}

run "plan_reads_state_but_only_writes_locks" {
  override_resource {
    target = aws_s3_bucket.state
    values = {
      arn = "arn:aws:s3:::fashionstore-tfstate-123456789012"
    }
  }

  override_resource {
    target = aws_iam_policy.plan_state_locks
    values = {
      arn = "arn:aws:iam::123456789012:policy/fashionstore-tfstate-plan-locks"
    }
  }

  assert {
    condition     = aws_iam_role_policy_attachment.plan_readonly.policy_arn == "arn:aws:iam::aws:policy/ReadOnlyAccess"
    error_message = "Plan must retain read access for state and infrastructure refresh"
  }

  assert {
    condition     = aws_iam_role_policy_attachment.plan_state.policy_arn == aws_iam_policy.plan_state_locks.arn
    error_message = "Plan must use the lock-only policy, not the apply state policy"
  }

  assert {
    condition = length(data.aws_iam_policy_document.plan_state_locks.statement) == 1 && alltrue([
      for s in data.aws_iam_policy_document.plan_state_locks.statement :
      toset(s.actions) == toset(["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]) &&
      toset(s.resources) == toset(["${aws_s3_bucket.state.arn}/*.tflock"])
    ])
    error_message = "Plan may read, create and delete .tflock objects only; it must not modify state files"
  }

  assert {
    condition     = aws_iam_role_policy_attachment.apply_state.policy_arn == aws_iam_policy.state_access.arn
    error_message = "Apply must retain its separate state write policy"
  }
}
