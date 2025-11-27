# Data
data "aws_availability_zones" "available" {}

########################################
# VPC, Subnets, Internet Gateway, NAT
########################################

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "${var.project_name}-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.this.id
  tags = { Name = "${var.project_name}-igw" }
}

# Map CIDR -> AZ deterministically using availability zones
locals {
  # If there are more CIDRs than AZs, wrap around using modulo
  public_map = {
    for idx, cidr in tolist(var.public_subnet_cidrs) :
    cidr => data.aws_availability_zones.available.names[idx % length(data.aws_availability_zones.available.names)]
  }

  private_map = {
    for idx, cidr in tolist(var.private_subnet_cidrs) :
    cidr => data.aws_availability_zones.available.names[idx % length(data.aws_availability_zones.available.names)]
  }
}

resource "aws_subnet" "public" {
  for_each = local.public_map

  vpc_id                  = aws_vpc.this.id
  cidr_block              = each.key
  availability_zone       = each.value
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.project_name}-public-${replace(each.key, "/", "-")}"
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip"
  }
}

# Choose the first public subnet (by input order) for the NAT gateway
# This uses the CIDR string that is first in the var.public_subnet_cidrs list.
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  # reference the created public subnet by its CIDR key
  subnet_id = aws_subnet.public[ var.public_subnet_cidrs[0] ].id
  depends_on = [aws_internet_gateway.igw]
  tags = { Name = "${var.project_name}-natgw" }
}

resource "aws_subnet" "private" {
  for_each = local.private_map

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.key
  availability_zone = each.value
  map_public_ip_on_launch = false
  tags = {
    Name = "${var.project_name}-private-${replace(each.key, "/", "-")}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags = { Name = "${var.project_name}-public-rt" }
}

# Route to Internet Gateway for public route table
resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_route_table_association" "public_assoc" {
  for_each = aws_subnet.public
  subnet_id = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id
  tags = { Name = "${var.project_name}-private-rt" }
}

# Route private subnets to NAT gateway for outbound internet access
resource "aws_route" "private_nat" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat.id
}

resource "aws_route_table_association" "private_assoc" {
  for_each = aws_subnet.private
  subnet_id = each.value.id
  route_table_id = aws_route_table.private.id
}

########################################
# Security Groups
########################################

resource "aws_security_group" "lambda_sg" {
  name = "${var.project_name}-lambda-sg"
  vpc_id = aws_vpc.this.id
  description = "Security group for Lambda functions"

  egress {
    description = "Allow all outbound"
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-lambda-sg" }
}

resource "aws_security_group" "rds_sg" {
  name = "${var.project_name}-rds-sg"
  vpc_id = aws_vpc.this.id
  description = "RDS SG allowing MySQL from Lambdas"

  ingress {
    description = "MySQL from lambdas"
    from_port = 3306
    to_port = 3306
    protocol = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-rds-sg" }
}

########################################
# RDS Subnet Group and Instance
########################################

resource "aws_db_subnet_group" "this" {
  name = "${var.project_name}-db-subnet-group"
  subnet_ids = values(aws_subnet.private)[*].id
  tags = { Name = "${var.project_name}-db-subnet-group" }
}

resource "aws_db_instance" "this" {
  identifier = "${var.project_name}-db"
  allocated_storage = var.db_allocated_storage
  engine = "mysql"
  engine_version = "8.0"
  instance_class = var.db_instance_class
  db_name = "Shoeshop"
  username = var.db_username
  password = var.db_password
  db_subnet_group_name = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot = true
  publicly_accessible = var.enable_rds_public_access
  tags = { Name = "${var.project_name}-rds" }
  depends_on = [aws_nat_gateway.nat]
}

########################################
# Secrets Manager for DB credentials
########################################

resource "aws_secretsmanager_secret" "db" {
  name = "${var.project_name}-db-credentials"
  description = "DB credentials for shoe-reco"
}

resource "aws_secretsmanager_secret_version" "db_version" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username,
    password = var.db_password,
    host = aws_db_instance.this.address,
    port = aws_db_instance.this.port,
    dbname = "Shoeshop"
  })
  depends_on = [aws_db_instance.this]
}

########################################
# IAM for Lambdas
########################################

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect = "Allow"
    principals {
      type = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags = { Name = "${var.project_name}-lambda-role" }
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_inline_doc" {
  # Secrets Manager access
  statement {
    sid    = "SecretsAccess"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = [aws_secretsmanager_secret.db.arn]
  }

  # RDS access
  statement {
    sid    = "RDSConnect"
    effect = "Allow"
    actions = [
      "rds-db:connect",
      "rds:DescribeDBInstances"
    ]
    resources = ["*"]
  }

  # Bedrock access
  statement {
    sid    = "Bedrock"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:InvokeAgent"
    ]
    resources = ["*"]
  }

  # SES email permissions
  statement {
    sid    = "SES"
    effect = "Allow"
    actions = [
      "ses:SendEmail",
      "ses:SendRawEmail"
    ]
    resources = ["*"]
  }

  # CloudWatch logs
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }

  #############################################
  # NEW — REQUIRED FOR VPC LAMBDAS
  #############################################
  statement {
    sid    = "VpcLambdaNetworking"
    effect = "Allow"
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface"
    ]
    resources = ["*"]
  }
}


resource "aws_iam_policy" "lambda_inline" {
  name = "${var.project_name}-lambda-inline-policy"
  policy = data.aws_iam_policy_document.lambda_inline_doc.json
}

resource "aws_iam_role_policy_attachment" "lambda_inline_attach" {
  role = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_inline.arn
}

########################################
# S3 bucket for lambda artifacts
########################################

resource "random_id" "bucket_id" {
  byte_length = 4
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.project_name}-lambda-artifacts-${random_id.bucket_id.hex}"
  force_destroy = true
  tags = { Name = "${var.project_name}-lambda-artifacts" }
}

########################################
# Lambda functions (S3-based)
########################################

locals {
  lambda_map = {
    bedrock_agent = { s3_key = "bedrock_agent.zip", memory = 512, timeout = 30 }
    get_customer  = { s3_key = "get_customer.zip", memory = 256, timeout = 15 }
    new_user      = { s3_key = "new_user.zip", memory = 256, timeout = 15 }
    create_order  = { s3_key = "create_order.zip", memory = 256, timeout = 20 }
  }
}

resource "aws_lambda_function" "functions" {
  for_each = local.lambda_map

  function_name = "${var.project_name}-${each.key}"
  s3_bucket     = aws_s3_bucket.artifacts.id
  s3_key        = each.value.s3_key
  handler       = "index.lambda_handler"
  runtime       = var.lambda_runtime
  role          = aws_iam_role.lambda_role.arn
  memory_size   = each.value.memory
  timeout       = each.value.timeout

  vpc_config {
    subnet_ids = values(aws_subnet.private)[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      DB_SECRET_ARN = aws_secretsmanager_secret.db.arn
      DB_HOST       = aws_db_instance.this.address
      DB_NAME       = "Shoeshop"
      SES_FROM      = var.ses_from_email
      REGION        = var.aws_region
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_basic]
}

########################################
# API Gateway HTTP API (Bedrock agent entry)
########################################

resource "aws_apigatewayv2_api" "http_api" {
  name = "${var.project_name}-http-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "agent_integration" {
  api_id = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"
  integration_uri = aws_lambda_function.functions["bedrock_agent"].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_route" {
  api_id = aws_apigatewayv2_api.http_api.id
  route_key = "POST /"
  target = "integrations/${aws_apigatewayv2_integration.agent_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id = aws_apigatewayv2_api.http_api.id
  name = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "allow_apigw" {
  statement_id = "AllowAPIGWInvoke"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions["bedrock_agent"].function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
