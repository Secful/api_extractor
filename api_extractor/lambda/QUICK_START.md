# Lambda Deployment Quick Start

## First-Time Setup

```bash
# 1. Configure AWS credentials
aws configure

# 2. Edit configuration
nano lambda-config.sh

# 3. Setup VPC
make setup-vpc

# 4. Setup S3 Files
make setup-s3

# 5. Upload code to S3
aws s3 cp --recursive ./my-project s3://my-code-repositories/my-project/

# 6. Build and deploy
make lambda-deploy

# 7. Attach S3 filesystem
make attach-s3-files

# 8. Create Function URL
make lambda-url
```

## Update Existing Function

```bash
# Rebuild and redeploy
make lambda-deploy
```

## Test

```bash
# Test specific folder
bash scripts/test_lambda_remote.sh my-fastapi-app

# Or use default test
make lambda-test
```

## View Logs

```bash
# Real-time logs
aws logs tail /aws/lambda/api-extractor --follow

# Recent logs
aws logs tail /aws/lambda/api-extractor --since 10m
```

## Cleanup

```bash
# Remove Lambda function (keeps S3 bucket and VPC)
make cleanup
```

## Common Issues

### "S3 filesystem not mounted"
```bash
make attach-s3-files
```

### "Folder not found"
```bash
# Upload folder to S3
aws s3 cp --recursive ./my-project s3://my-code-repositories/my-project/

# Verify
aws s3 ls s3://my-code-repositories/
```

### Timeout
```bash
# Edit lambda-config.sh
export LAMBDA_TIMEOUT=600

# Redeploy
make lambda-deploy
```

## Request Examples

### Minimal
```json
{"folder": "my-project"}
```

### Full
```json
{
  "folder": "my-fastapi-app",
  "title": "My API",
  "version": "1.0.0",
  "description": "Production API"
}
```

## Test with awscurl

```bash
# Install
pip install awscurl

# Get URL
FUNCTION_URL=$(aws lambda get-function-url-config --function-name api-extractor --query 'FunctionUrl' --output text)

# Test
awscurl --service lambda --region us-east-1 -X POST \
  -H "Content-Type: application/json" \
  -d '{"folder": "my-project"}' \
  "$FUNCTION_URL"
```
