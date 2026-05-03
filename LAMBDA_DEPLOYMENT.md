# Lambda Deployment Guide

This guide explains how to deploy the API Extractor as an AWS Lambda function with S3 filesystem integration.

## Architecture

```
Client (with IAM creds)
    ↓
Lambda Function URL (IAM auth)
    ↓
Lambda Handler (Python 3.11 ARM64)
    ↓
ExtractionService.extract_api()
    ↓
Read from /mnt/s3/{folder} (S3 Files)
    ↓
Return OpenAPI JSON
```

## Prerequisites

1. **AWS CLI configured** with credentials
   ```bash
   aws configure
   ```

2. **Docker installed** (for building ARM64 packages)

3. **jq installed** (for JSON processing)
   ```bash
   brew install jq  # macOS
   apt-get install jq  # Ubuntu
   ```

## Configuration

Edit `lambda-config.sh` with your settings:

```bash
export FUNCTION_NAME=api-extractor
export AWS_REGION=us-east-1
export S3_BUCKET_NAME=my-code-repositories
export LAMBDA_TIMEOUT=300
export LAMBDA_MEMORY=1024
```

## Deployment Steps

### 1. Setup VPC (one-time)

The Lambda function needs VPC access to connect to S3 Files:

```bash
make setup-vpc
```

This creates:
- VPC with DNS enabled
- 2 subnets in different availability zones
- Internet Gateway
- NAT Gateway
- Route tables
- Security group allowing NFS traffic (port 2049)

### 2. Setup S3 Files (one-time)

Create S3 bucket and file system:

```bash
make setup-s3
```

This creates:
- S3 bucket (if it doesn't exist)
- S3 file system
- Mount targets in each subnet
- Access point for Lambda

### 3. Upload Code to S3

Upload your source code repositories to S3:

```bash
# Example: Upload a FastAPI project
aws s3 cp --recursive ./my-fastapi-app s3://my-code-repositories/my-fastapi-app/

# Verify upload
aws s3 ls s3://my-code-repositories/ --recursive
```

### 4. Build Lambda Package

Build the ARM64 deployment package:

```bash
make lambda-build
```

This creates `build/lambda-function.zip` with:
- ARM64-compiled dependencies
- api_extractor package
- lambda_handler.py

### 5. Deploy Lambda Function

Deploy the function:

```bash
make lambda-deploy
```

This:
- Creates IAM role with S3 read permissions
- Creates or updates Lambda function
- Configures VPC settings
- Sets environment variables

### 6. Attach S3 Files to Lambda

Mount the S3 filesystem:

```bash
make attach-s3-files
```

This attaches the S3 file system to Lambda at `/mnt/s3`.

### 7. Create Function URL

Create a public URL with IAM authentication:

```bash
make lambda-url
```

This creates a Function URL that requires AWS Signature Version 4 authentication.

## Testing

### Test via AWS CLI

```bash
# Test with specific folder
bash scripts/test_lambda_remote.sh my-fastapi-app

# Or use make target
make lambda-test
```

### Test via Function URL

Install `awscurl` for SigV4 signing:

```bash
pip install awscurl
```

Get Function URL:

```bash
source lambda-config.sh
FUNCTION_URL=$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --query 'FunctionUrl' --output text)
```

Test API extraction:

```bash
awscurl --service lambda \
  --region us-east-1 \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"folder": "my-fastapi-app", "title": "My API", "version": "1.0.0"}' \
  "$FUNCTION_URL"
```

### View Logs

```bash
# Stream logs in real-time
aws logs tail /aws/lambda/api-extractor --follow

# Get recent logs
aws logs tail /aws/lambda/api-extractor --since 10m
```

## Request Format

```json
{
  "folder": "my-project",           // Required: folder name in S3
  "title": "My API",                 // Optional: OpenAPI title
  "version": "1.0.0",                // Optional: API version
  "description": "API description"   // Optional: API description
}
```

## Response Format

### Success (200)

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "My API",
    "version": "1.0.0"
  },
  "paths": {
    "/users": {
      "get": { ... }
    }
  }
}
```

Headers:
- `X-Endpoints-Count`: Number of endpoints extracted
- `X-Frameworks`: Comma-separated list of detected frameworks

### Error (4xx/5xx)

```json
{
  "error": "Error message",
  "errors": ["error 1", "error 2"],      // Optional
  "warnings": ["warning 1", "warning 2"]  // Optional
}
```

## Updating the Function

To update code:

```bash
make lambda-deploy
```

To update configuration:

```bash
# Edit lambda-config.sh
nano lambda-config.sh

# Redeploy
make lambda-deploy
```

## Cleanup

Remove all Lambda resources (preserves S3 bucket):

```bash
make cleanup
```

To also delete VPC resources, create `scripts/cleanup_vpc.sh` and run it separately.

## Cost Optimization

1. **Use ARM64 (Graviton)**: 20% cheaper than x86_64
2. **Right-size memory**: Start with 1024 MB, adjust based on CloudWatch metrics
3. **S3 Files caching**: Frequently accessed files are cached for low latency
4. **Reserved concurrency**: Set if you have predictable workloads

## Troubleshooting

### Lambda can't access S3 mount

Check:
1. VPC configuration is correct
2. Security group allows NFS (port 2049)
3. S3 Files mount targets are active
4. Lambda is in same VPC as mount targets

### Timeout errors

Increase timeout:
```bash
# Edit lambda-config.sh
export LAMBDA_TIMEOUT=600  # 10 minutes

# Redeploy
make lambda-deploy
```

### Out of memory

Increase memory:
```bash
# Edit lambda-config.sh
export LAMBDA_MEMORY=2048

# Redeploy
make lambda-deploy
```

### Cold start latency

- First invocation after deployment takes longer (cold start)
- Subsequent invocations are faster (warm start)
- Consider provisioned concurrency for predictable latency

## Security

- Function URL uses IAM authentication (AWS Signature v4)
- No public access without valid AWS credentials
- S3 bucket read-only access
- Logs sent to CloudWatch (encrypted at rest)

## Monitoring

View metrics in CloudWatch:
- Invocations
- Duration
- Errors
- Throttles
- Memory usage

## Supported Frameworks

The Lambda function supports all frameworks from api_extractor:

- **Python**: FastAPI, Flask, Django REST Framework
- **JavaScript/TypeScript**: Express, NestJS, Fastify
- **Java**: Spring Boot
- **C#**: ASP.NET Core
- **Go**: Gin

## Limitations

- Maximum execution time: 15 minutes (AWS Lambda limit)
- Maximum memory: 10 GB (AWS Lambda limit)
- S3 Files requires VPC (no direct internet access)
- Cold start latency: 2-5 seconds for first invocation

## Future Enhancements

1. **Caching**: Add CloudFront with cache based on S3 ETag
2. **Step Functions**: Handle very large repositories exceeding timeout
3. **EventBridge**: Trigger extraction on S3 upload events
4. **API Gateway**: Add REST API with API keys
