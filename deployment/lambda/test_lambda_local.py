"""Local test for Lambda handler."""

from __future__ import annotations

import json
import os
import sys

# Add api_extractor/lambda to path for handler import
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "api_extractor", "lambda"))

from handler import lambda_handler

# Set environment variables for local testing
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["S3_MOUNT_PATH"] = "/path/to/test/repos"  # Change this to local test path

# Mock event
event = {
    "body": json.dumps(
        {"folder": "test-fastapi-project", "title": "Test API", "version": "1.0.0"}
    )
}


# Mock context
class Context:
    """Mock Lambda context."""

    aws_request_id = "test-request-id"
    function_name = "api-extractor"


print("Testing Lambda handler locally...")
result = lambda_handler(event, Context())
print(f"Status Code: {result['statusCode']}")
print(f"Headers: {result['headers']}")

if result["statusCode"] == 200:
    print("\nOpenAPI Spec:")
    print(json.dumps(json.loads(result["body"]), indent=2))
else:
    print(f"\nError: {result['body']}")
