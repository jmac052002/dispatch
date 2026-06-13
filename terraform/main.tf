terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  required_version = ">= 1.6.0"
}

provider "aws" {
  region = var.aws_region
}

# --- S3 bucket for triage summaries ---
resource "aws_s3_bucket" "triage" {
  bucket = "${var.project_name}-triage-${var.aws_account_id}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "triage" {
  bucket = aws_s3_bucket.triage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "triage" {
  bucket = aws_s3_bucket.triage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "triage" {
  bucket                  = aws_s3_bucket.triage.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- ECR repository ---
resource "aws_ecr_repository" "dispatch" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# --- Secrets Manager ---
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name                    = "${var.project_name}/anthropic-api-key"
  recovery_window_in_days = 7

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

resource "aws_secretsmanager_secret" "github_token" {
  name                    = "${var.project_name}/github-token"
  recovery_window_in_days = 7

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "github_token" {
  secret_id     = aws_secretsmanager_secret.github_token.id
  secret_string = var.github_token
}

resource "aws_secretsmanager_secret" "webhook_secret" {
  name                    = "${var.project_name}/webhook-secret"
  recovery_window_in_days = 7

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "webhook_secret" {
  secret_id     = aws_secretsmanager_secret.webhook_secret.id
  secret_string = var.webhook_secret
}

# --- Lambda function ---
resource "aws_lambda_function" "dispatch" {
  function_name = var.project_name
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.dispatch.repository_url}:latest"
  timeout       = 300
  memory_size   = 512
  architectures  = ["arm64"]

  environment {
    variables = {
      ANTHROPIC_API_KEY = var.anthropic_api_key
      GITHUB_TOKEN      = var.github_token
      GITHUB_REPO       = var.github_repo
      WEBHOOK_SECRET    = var.webhook_secret
      S3_BUCKET         = aws_s3_bucket.triage.id
      AWS_ACCOUNT_ID    = var.aws_account_id
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_exec]
}

# --- API Gateway ---
resource "aws_apigatewayv2_api" "dispatch" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_apigatewayv2_integration" "dispatch" {
  api_id                 = aws_apigatewayv2_api.dispatch.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.dispatch.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "webhook" {
  api_id    = aws_apigatewayv2_api.dispatch.id
  route_key = "POST /webhook/github"
  target    = "integrations/${aws_apigatewayv2_integration.dispatch.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.dispatch.id
  name        = "$default"
  auto_deploy = true

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dispatch.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.dispatch.execution_arn}/*/*"
}