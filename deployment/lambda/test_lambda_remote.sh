#!/bin/bash
set -e

source lambda-config.sh

echo "Testing deployed Lambda function..."

FOLDER_NAME=${1:-"test-project"}

echo "Invoking function for folder: $FOLDER_NAME"

aws lambda invoke \
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
