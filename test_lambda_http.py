#!/usr/bin/env python3
"""Test Lambda Function URL with S3 Files."""

from __future__ import annotations

import argparse
import json
import sys
import time

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


def test_lambda(
    folder: str,
    title: str | None = None,
    version: str = "1.0.0",
    description: str | None = None,
) -> requests.Response:
    """Test Lambda via HTTP with IAM auth.

    Args:
        folder: Folder name in S3 (relative to /lambda/)
        title: OpenAPI title (optional, defaults to folder name)
        version: API version
        description: API description

    Returns:
        HTTP response from Lambda
    """
    session = boto3.Session()
    credentials = session.get_credentials()

    function_url = "https://ahzvsgyknbsk3i6m2duocbslbu0ktlzw.lambda-url.eu-north-1.on.aws/"

    payload = {
        "folder": folder,
        "title": title or f"{folder} API",
        "version": version,
    }

    if description:
        payload["description"] = description

    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload)

    request = AWSRequest(method="POST", url=function_url, data=body, headers=headers)
    SigV4Auth(credentials, "lambda", "eu-north-1").add_auth(request)

    response = requests.post(
        function_url, headers=dict(request.headers), data=body, timeout=310
    )
    return response


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Lambda Function URL with S3 Files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s spring-boot-realworld
  %(prog)s spring-boot-realworld --title "My API" --version "2.0.0"
  %(prog)s test-fastapi --no-retry
        """,
    )

    parser.add_argument("folder", help="Folder name in S3 (relative to /lambda/)")
    parser.add_argument("--title", help="OpenAPI title (default: <folder> API)")
    parser.add_argument("--version", default="1.0.0", help="API version (default: 1.0.0)")
    parser.add_argument("--description", help="API description")
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Max retry attempts for transient errors (default: 3)",
    )
    parser.add_argument(
        "--no-retry", action="store_true", help="Disable retries, fail immediately"
    )
    parser.add_argument(
        "--output",
        default="extracted_openapi.json",
        help="Output file path (default: extracted_openapi.json)",
    )

    args = parser.parse_args()

    max_attempts = 1 if args.no_retry else args.max_attempts

    print("🧪 Testing Lambda Function URL with S3 Files")
    print("=" * 70)
    print(f"Function: api-extractor")
    print(f"Region: eu-north-1")
    print(f"Folder: {args.folder}")
    print(f"S3 Path: s3://my-code-repositories/lambda/{args.folder}/")
    if args.title:
        print(f"Title: {args.title}")
    print("=" * 70)
    print()

    for attempt in range(1, max_attempts + 1):
        if max_attempts > 1:
            print(f"📡 Attempt {attempt}/{max_attempts} - {time.strftime('%H:%M:%S')}")

        try:
            start_time = time.time()
            response = test_lambda(
                folder=args.folder,
                title=args.title,
                version=args.version,
                description=args.description,
            )
            elapsed = time.time() - start_time

            print(f"   ⏱️  Execution Time: {elapsed:.2f}s")
            print(f"   📊 Status: {response.status_code}")

            # Show custom headers
            custom_headers = {
                k: v for k, v in response.headers.items() if k.startswith("X-")
            }
            if custom_headers and custom_headers.get("X-Frameworks"):
                print(f"   🔧 Frameworks: {custom_headers.get('X-Frameworks')}")
                print(f"   📍 Endpoints: {custom_headers.get('X-Endpoints-Count', 'N/A')}")

            if response.status_code == 200:
                print("\n✅ SUCCESS! Lambda executed successfully!\n")

                spec = response.json()
                info = spec.get("info", {})
                paths = spec.get("paths", {})
                components = spec.get("components", {})

                print(f"OpenAPI Version: {spec.get('openapi')}")
                print(f"Title: {info.get('title')}")
                print(f"Version: {info.get('version')}")
                if info.get("description"):
                    desc = info["description"]
                    print(f"Description: {desc[:80]}{'...' if len(desc) > 80 else ''}")

                print(f"\n📊 Statistics:")
                print(f"   Endpoints: {len(paths)}")
                print(f"   Schemas: {len(components.get('schemas', {}))}")

                if paths:
                    print(f"\n🔗 Extracted Endpoints:")
                    for i, (path, methods) in enumerate(sorted(paths.items()), 1):
                        method_list = [m.upper() for m in methods.keys() if m != "parameters"]
                        method_str = ", ".join(m.ljust(6) for m in method_list)
                        print(f"   {i:2}. {method_str} {path}")

                # Save result
                with open(args.output, "w") as f:
                    json.dump(spec, f, indent=2)

                import os

                file_size = os.path.getsize(args.output)
                print(f"\n💾 Full spec saved to: {args.output}")
                print(f"   File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

                return 0

            elif response.status_code == 404:
                print("\n   ❌ Folder not found in S3")
                print(f"   Make sure folder exists at: s3://my-code-repositories/lambda/{args.folder}/")
                return 1

            elif response.status_code == 422:
                print("\n   ⚠️  Extraction failed (unprocessable entity)")
                try:
                    error = response.json()
                    if error.get("errors"):
                        print("   Errors:")
                        for err in error["errors"]:
                            print(f"     - {err}")
                except:
                    pass
                return 1

            elif response.status_code >= 500:
                error_type = response.headers.get("x-amzn-ErrorType", "")
                if "S3FilesMountConnectivity" in error_type:
                    print("   ⏳ Mount targets still initializing...")
                elif "S3FilesMountFailure" in error_type:
                    print("   ❌ Failed to mount S3 Files")
                    return 1
                else:
                    print(f"   ⚠️  Server Error: {error_type or 'Internal Error'}")

                if attempt < max_attempts:
                    print(f"   💤 Retrying in 30 seconds...\n")
                    time.sleep(30)
            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return 1

        except requests.exceptions.Timeout:
            print("   ⏱️  Request timeout (Lambda execution > 5 minutes)")
            return 1
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            return 130
        except Exception as e:
            print(f"   ❌ Exception: {str(e)[:200]}")
            import traceback

            traceback.print_exc()
            return 1

    print("\n" + "=" * 70)
    print("❌ All attempts failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
