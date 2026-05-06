#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "Testing deployed Lambda function in region: $AWS_REGION"

FOLDER_NAME=${1:-"test-project"}

echo "Invoking function for folder: $FOLDER_NAME"

aws lambda invoke \
    --region "$AWS_REGION" \
    --function-name "$FUNCTION_NAME" \
    --cli-binary-format raw-in-base64-out \
    --payload "{\"folder\": \"$FOLDER_NAME\"}" \
    --log-type Tail \
    --query 'LogResult' \
    --output text response.json | base64 --decode

echo ""
echo "Response:"
cat response.json | jq '.'

echo ""
echo "OpenAPI spec saved to: response.json"
