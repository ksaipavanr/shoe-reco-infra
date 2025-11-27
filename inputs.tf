variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "shoe-reco"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  type = list(string)
  default = ["10.0.1.0/24","10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  type = list(string)
  default = ["10.0.11.0/24","10.0.12.0/24"]
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "enable_rds_public_access" {
  type    = bool
  default = false
}

variable "lambda_runtime" {
  type    = string
  default = "python3.11"
}

variable "lambda_memory" {
  type    = number
  default = 256
}

variable "lambda_timeout" {
  type    = number
  default = 30
}

variable "ses_from_email" {
  type    = string
  default = ""
}
