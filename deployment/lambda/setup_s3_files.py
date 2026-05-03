#!/usr/bin/env python3
"""Setup S3 Files filesystem for Lambda."""

import json
import os
import subprocess
import sys
import time

import boto3
from botocore.exceptions import ClientError

# Load configuration from lambda-config.sh
def load_config():
    """Load configuration from lambda-config.sh."""
    config = {}
    with open("lambda-config.sh") as f:
        for line in f:
            if line.startswith("export "):
                line = line.replace("export ", "").strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key] = value.strip('"')
    return config

def save_config(config_vars):
    """Save configuration variables to lambda-config.sh."""
    with open("lambda-config.sh", "a") as f:
        f.write("\n# S3 Files Configuration (auto-generated)\n")
        for key, value in config_vars.items():
            f.write(f"export {key}={value}\n")

def main():
    config = load_config()

    region = config["AWS_REGION"]
    bucket_name = config["S3_BUCKET_NAME"]
    function_name = config["FUNCTION_NAME"]
    subnet_ids = config["SUBNET_IDS"].split()

    print(f"Setting up S3 Files for bucket: {bucket_name}")

    # Initialize clients
    s3 = boto3.client("s3", region_name=region)
    s3files = boto3.client("s3files", region_name=region)
    iam = boto3.client("iam", region_name=region)
    sts = boto3.client("sts", region_name=region)

    # Get account ID
    account_id = sts.get_caller_identity()["Account"]

    # Check if bucket exists, create if not
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} already exists")
    except ClientError:
        print(f"Creating S3 bucket {bucket_name}...")
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region}
            )

    bucket_arn = f"arn:aws:s3:::{bucket_name}"

    # Enable versioning (required for S3 Files)
    print("Enabling S3 versioning...")
    s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"Status": "Enabled"}
    )

    # Create IAM role for S3 Files
    s3files_role_name = f"{function_name}-s3files-role"

    try:
        role_response = iam.get_role(RoleName=s3files_role_name)
        s3files_role_arn = role_response["Role"]["Arn"]
        print(f"S3 Files IAM role already exists: {s3files_role_arn}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            print(f"Creating IAM role for S3 Files: {s3files_role_name}")

            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowS3FilesAssumeRole",
                        "Effect": "Allow",
                        "Principal": {"Service": "elasticfilesystem.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": account_id
                            },
                            "ArnLike": {
                                "aws:SourceArn": f"arn:aws:s3files:{region}:{account_id}:file-system/*"
                            }
                        }
                    }
                ]
            }

            role_response = iam.create_role(
                RoleName=s3files_role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"S3 Files role for {function_name}"
            )
            s3files_role_arn = role_response["Role"]["Arn"]

            # Attach S3 access policy (as per AWS documentation)
            s3_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "S3BucketPermissions",
                        "Effect": "Allow",
                        "Action": [
                            "s3:ListBucket",
                            "s3:ListBucketVersions"
                        ],
                        "Resource": bucket_arn,
                        "Condition": {
                            "StringEquals": {
                                "aws:ResourceAccount": account_id
                            }
                        }
                    },
                    {
                        "Sid": "S3ObjectPermissions",
                        "Effect": "Allow",
                        "Action": [
                            "s3:AbortMultipartUpload",
                            "s3:DeleteObject*",
                            "s3:GetObject*",
                            "s3:List*",
                            "s3:PutObject*"
                        ],
                        "Resource": f"{bucket_arn}/*",
                        "Condition": {
                            "StringEquals": {
                                "aws:ResourceAccount": account_id
                            }
                        }
                    },
                    {
                        "Sid": "EventBridgeManage",
                        "Effect": "Allow",
                        "Action": [
                            "events:DeleteRule",
                            "events:DisableRule",
                            "events:EnableRule",
                            "events:PutRule",
                            "events:PutTargets",
                            "events:RemoveTargets"
                        ],
                        "Condition": {
                            "StringEquals": {
                                "events:ManagedBy": "elasticfilesystem.amazonaws.com"
                            }
                        },
                        "Resource": [
                            "arn:aws:events:*:*:rule/DO-NOT-DELETE-S3-Files*"
                        ]
                    },
                    {
                        "Sid": "EventBridgeRead",
                        "Effect": "Allow",
                        "Action": [
                            "events:DescribeRule",
                            "events:ListRuleNamesByTarget",
                            "events:ListRules",
                            "events:ListTargetsByRule"
                        ],
                        "Resource": [
                            "arn:aws:events:*:*:rule/*"
                        ]
                    }
                ]
            }

            iam.put_role_policy(
                RoleName=s3files_role_name,
                PolicyName=f"{function_name}-s3files-bucket-access",
                PolicyDocument=json.dumps(s3_policy)
            )

            print("Waiting for IAM role to propagate...")
            time.sleep(10)
        else:
            raise

    # Create S3 file system
    print("Creating S3 file system...")
    try:
        fs_response = s3files.create_file_system(
            bucket=bucket_arn,  # Use bucket ARN
            roleArn=s3files_role_arn
        )
        file_system_id = fs_response["fileSystemId"]
        print(f"File system created: {file_system_id}")
    except ClientError as e:
        if "FileSystemAlreadyExists" in str(e) or "AlreadyExists" in str(e):
            # List file systems to find existing one
            fs_list = s3files.list_file_systems(bucket=bucket_arn)
            file_system_id = fs_list["fileSystems"][0]["fileSystemId"]
            print(f"File system already exists: {file_system_id}")
        else:
            raise

    # Create mount targets in each subnet
    print("Creating mount targets...")
    for subnet_id in subnet_ids:
        try:
            print(f"Creating mount target in subnet: {subnet_id}")
            s3files.create_mount_target(
                fileSystemId=file_system_id,
                subnetId=subnet_id
            )
        except ClientError as e:
            if "MountTargetConflict" in str(e) or "AlreadyExists" in str(e):
                print(f"Mount target already exists in subnet {subnet_id}")
            else:
                print(f"Warning: Could not create mount target in {subnet_id}: {e}")

    print("\nWaiting for mount targets to become available (this can take up to 15 minutes)...")
    print("Checking status...")

    max_wait = 900  # 15 minutes
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            mt_list = s3files.list_mount_targets(fileSystemId=file_system_id)
            mount_targets = mt_list.get("mountTargets", [])

            if not mount_targets:
                print("No mount targets found yet, waiting...")
                time.sleep(30)
                continue

            all_available = all(
                mt.get("lifeCycleState") == "available" or mt.get("lifecycleState") == "available"
                for mt in mount_targets
            )

            if all_available:
                print("All mount targets are available!")
                break

            statuses = [mt.get('lifeCycleState') or mt.get('lifecycleState') for mt in mount_targets]
            print(f"Mount targets status: {statuses}")
            time.sleep(30)
        except Exception as e:
            print(f"Checking status: {e}")
            time.sleep(30)

    # Save configuration
    save_config({
        "FILE_SYSTEM_ID": file_system_id,
        "S3FILES_ROLE_ARN": s3files_role_arn
    })

    print("\n" + "="*50)
    print("S3 Files setup complete!")
    print(f"File System ID: {file_system_id}")
    print(f"Bucket: {bucket_name}")
    print(f"Role ARN: {s3files_role_arn}")
    print("="*50)

if __name__ == "__main__":
    main()
