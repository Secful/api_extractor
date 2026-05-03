#!/bin/bash
set -e

echo "Building Lambda deployment package for ARM64..."

# Clean previous builds
rm -rf build/
mkdir -p build/lambda-package

# Use Docker to build for ARM64 (Graviton)
docker run --rm --platform linux/arm64 \
    -v "$(pwd)":/workspace \
    -w /workspace \
    --entrypoint /bin/bash \
    public.ecr.aws/lambda/python:3.11-arm64 \
    -c "pip install --target build/lambda-package -r lambda_requirements.txt && \
        cp -r api_extractor build/lambda-package/ && \
        cp lambda_handler.py build/lambda-package/"

# Create ZIP
cd build/lambda-package
zip -r ../lambda-function.zip . -x '*.pyc' -x '__pycache__/*' -q
cd ../..

echo "Package created: build/lambda-function.zip"
ls -lh build/lambda-function.zip
