.PHONY: lambda-build lambda-deploy lambda-test clean setup-s3 setup-vpc lambda-url attach-s3-files

setup-vpc:
	@echo "Setting up VPC..."
	bash scripts/setup_vpc.sh

setup-s3:
	@echo "Setting up S3 Files..."
	bash scripts/setup_s3_files.sh

lambda-build:
	@echo "Building Lambda package for ARM64..."
	bash scripts/build_lambda.sh

lambda-deploy: lambda-build
	@echo "Deploying Lambda function..."
	bash scripts/deploy_lambda.sh

attach-s3-files:
	@echo "Attaching S3 Files to Lambda..."
	bash scripts/attach_s3_files.sh

lambda-url:
	@echo "Creating Function URL..."
	bash scripts/create_function_url.sh

lambda-test:
	@echo "Testing Lambda function..."
	aws lambda invoke \
		--function-name api-extractor \
		--cli-binary-format raw-in-base64-out \
		--payload '{"folder": "test-project"}' \
		response.json
	cat response.json | jq .

clean:
	rm -rf build/
	rm -f response.json

cleanup:
	@echo "Cleaning up all AWS resources..."
	bash scripts/cleanup.sh
