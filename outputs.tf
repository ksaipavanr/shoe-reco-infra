output "api_endpoint" {
  description = "HTTP API endpoint"
  value = aws_apigatewayv2_api.http_api.api_endpoint
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value = aws_db_instance.this.address
}

output "lambda_function_names" {
  description = "Lambda functions deployed"
  value = [for k, f in aws_lambda_function.functions : f.function_name]
}

output "s3_artifacts_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}
