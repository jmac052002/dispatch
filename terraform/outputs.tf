output "api_gateway_url" {
  description = "Public URL for the webhook endpoint"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/webhook/github"
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing Docker images"
  value       = aws_ecr_repository.dispatch.repository_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.dispatch.function_name
}

output "triage_bucket_name" {
  description = "S3 bucket where triage summaries are saved"
  value       = aws_s3_bucket.triage.bucket
}

output "anthropic_secret_arn" {
  description = "ARN of the Anthropic API key secret"
  value       = aws_secretsmanager_secret.anthropic_api_key.arn
}