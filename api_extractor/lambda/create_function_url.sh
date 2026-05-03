#!/bin/bash
set -e

# Load configuration
source lambda-config.sh

echo "Creating Function URL for: $FUNCTION_NAME"

# Check if Function URL already exists
FUNCTION_URL=$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --query 'FunctionUrl' --output text 2>/dev/null || echo "")

if [ -z "$FUNCTION_URL" ]; then
    echo "Creating Function URL with IAM authentication..."
    aws lambda create-function-url-config \
        --function-name "$FUNCTION_NAME" \
        --auth-type AWS_IAM \
        --cors '{
            "AllowCredentials": true,
            "AllowOrigins": ["*"],
            "AllowMethods": ["POST"],
            "AllowHeaders": ["content-type", "x-amz-date", "authorization", "x-api-key"],
            "MaxAge": 86400
        }'

    FUNCTION_URL=$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --query 'FunctionUrl' --output text)
else
    echo "Function URL already exists"
fi

echo ""
echo "========================================="
echo "Function URL: $FUNCTION_URL"
echo "========================================="
echo ""
echo "To test with IAM authentication:"
echo "  aws lambda invoke \\"
echo "    --function-name $FUNCTION_NAME \\"
echo "    --payload '{\"folder\": \"test-project\"}' \\"
echo "    response.json"
echo ""
