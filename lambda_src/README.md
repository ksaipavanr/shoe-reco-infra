# Shoe Recommendation Chatbot – Terraform Infrastructure

This repository contains the Terraform configuration for deploying a simplified infrastructure setup for the Shoe Recommendation Chatbot as requested in the assignment.

The goal is to demonstrate the ability to design and provision AWS resources using Terraform, including Lambda, API Gateway, RDS, IAM, and supporting components.

---

## 🚀 Infrastructure Components Provisioned

### 1. **AWS Lambda**
- One Lambda function (placeholder code supplied in `lambda_src/`).
- Packaged and uploaded to an S3 bucket created through Terraform.
- Connected to API Gateway.

### 2. **API Gateway (HTTP API)**
- A single POST endpoint.
- Invokes the Lambda function.
- CORS enabled.

### 3. **Amazon RDS (MySQL or PostgreSQL)**
- A lightweight RDS instance deployed inside private subnets.
- Username, password, DB name defined through Terraform variables.
- Security group configured to allow Lambda access.

### 4. **Networking (Optional VPC Enhancement)**
- Custom VPC with:
  - 2 public subnets
  - 2 private subnets
  - Internet Gateway
  - NAT Gateway
  - Route tables
- Lambda is deployed in private subnets.
- RDS is private and not publicly accessible.

### 5. **IAM Roles & Permissions**
- Lambda Execution Role with:
  - CloudWatch Logs access
  - Mock Bedrock permissions (as required)
  - RDS access via security groups
  - S3 read access for Lambda code artifacts

### 6. **Optional (Good to Have) – SES**
- Verified SES identity resource included (optional).
- IAM permission for Lambda to send email (mock setup).



