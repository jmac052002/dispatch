variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "dispatch"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

variable "github_token" {
  description = "GitHub personal access token"
  type        = string
  sensitive   = true
}

variable "github_repo" {
  description = "GitHub repository in owner/repo format"
  type        = string
  default     = "jmac052002/dispatch"
}

variable "webhook_secret" {
  description = "Secret for validating GitHub webhook signatures"
  type        = string
  sensitive   = true
}