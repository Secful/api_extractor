"""CLI interface for API Extractor."""

import sys
import click
from typing import List, Optional
from pathlib import Path

from api_extractor.core.detector import FrameworkDetector
from api_extractor.core.models import FrameworkType, ExtractionResult
from api_extractor.openapi.builder import OpenAPIBuilder
from api_extractor.input_handlers.local import LocalHandler
from api_extractor.input_handlers.s3 import S3Handler


def get_extractor(framework: FrameworkType):
    """
    Get extractor instance for framework.

    Args:
        framework: Framework type

    Returns:
        Extractor instance
    """
    if framework == FrameworkType.FASTAPI:
        from api_extractor.extractors.python.fastapi import FastAPIExtractor

        return FastAPIExtractor()
    elif framework == FrameworkType.FLASK:
        from api_extractor.extractors.python.flask import FlaskExtractor

        return FlaskExtractor()
    elif framework == FrameworkType.DJANGO_REST:
        from api_extractor.extractors.python.django_rest import DjangoRESTExtractor

        return DjangoRESTExtractor()
    elif framework == FrameworkType.EXPRESS:
        from api_extractor.extractors.javascript.express import ExpressExtractor

        return ExpressExtractor()
    elif framework == FrameworkType.NESTJS:
        from api_extractor.extractors.javascript.nestjs import NestJSExtractor

        return NestJSExtractor()
    elif framework == FrameworkType.FASTIFY:
        from api_extractor.extractors.javascript.fastify import FastifyExtractor

        return FastifyExtractor()
    else:
        return None


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """API Extractor - Extract REST API definitions from source code."""
    pass


@cli.command()
@click.argument("path", type=str)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="openapi.json",
    help="Output file path (default: openapi.json)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--framework",
    "-w",
    multiple=True,
    type=click.Choice(
        [f.value for f in FrameworkType],
        case_sensitive=False,
    ),
    help="Manually specify framework(s), bypasses detection",
)
@click.option(
    "--s3",
    is_flag=True,
    help="Treat path as S3 URI (s3://bucket/path/)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed extraction progress",
)
@click.option(
    "--title",
    type=str,
    default="Extracted API",
    help="API title for OpenAPI spec",
)
@click.option(
    "--version",
    type=str,
    default="1.0.0",
    help="API version for OpenAPI spec",
)
def extract(
    path: str,
    output: str,
    format: str,
    framework: tuple,
    s3: bool,
    verbose: bool,
    title: str,
    version: str,
):
    """
    Extract API definitions from source code.

    PATH: Path to codebase (local directory or S3 URI with --s3 flag)
    """
    try:
        # Determine input handler
        if s3:
            handler = S3Handler()
            if verbose:
                click.echo("Using S3 handler...")
        else:
            handler = LocalHandler()
            if verbose:
                click.echo("Using local filesystem handler...")

        # Validate source
        if not handler.is_valid_source(path):
            if s3:
                click.echo(f"Error: Invalid S3 URI: {path}", err=True)
            else:
                click.echo(f"Error: Path not found or not a directory: {path}", err=True)
            sys.exit(2)

        # Get local path
        local_path = handler.get_path(path)
        if not local_path:
            click.echo(f"Error: Failed to access source: {path}", err=True)
            sys.exit(2)

        if verbose:
            click.echo(f"Processing: {local_path}")

        # Detect or use specified frameworks
        frameworks: Optional[List[FrameworkType]] = None

        if framework:
            # Manual framework specification
            frameworks = [FrameworkType(f) for f in framework]
            if verbose:
                click.echo(f"Using manually specified frameworks: {', '.join(f.value for f in frameworks)}")
        else:
            # Automatic detection
            if verbose:
                click.echo("Detecting frameworks...")

            detector = FrameworkDetector()
            frameworks = detector.detect(local_path)

            if frameworks is None:
                click.echo("Error: Unable to detect any supported frameworks", err=True)
                click.echo(
                    "Suggestion: Use --framework to manually specify framework(s)",
                    err=True,
                )
                handler.cleanup()
                sys.exit(1)

            if verbose:
                for fw in frameworks:
                    click.echo(f"  ✓ Found: {fw.value}")

        # Extract routes from each framework
        if verbose:
            click.echo("Extracting routes...")

        all_endpoints = []
        all_errors = []
        all_warnings = []

        for fw in frameworks:
            extractor = get_extractor(fw)
            if not extractor:
                if verbose:
                    click.echo(f"  ! Skipping {fw.value}: extractor not yet implemented")
                continue

            result = extractor.extract(local_path)

            if result.success:
                all_endpoints.extend(result.endpoints)
                if verbose:
                    click.echo(f"  {fw.value}: {len(result.endpoints)} endpoints found")
            else:
                if verbose:
                    click.echo(f"  {fw.value}: No endpoints found")

            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        # Check if we found any endpoints
        if not all_endpoints:
            click.echo("Error: No API endpoints found", err=True)
            if all_errors:
                click.echo("\nErrors encountered:", err=True)
                for error in all_errors[:5]:  # Show first 5 errors
                    click.echo(f"  - {error}", err=True)
            handler.cleanup()
            sys.exit(3)

        # Generate OpenAPI spec
        if verbose:
            click.echo("Generating OpenAPI spec...")

        builder = OpenAPIBuilder(title=title, version=version)
        spec = builder.build(all_endpoints)

        # Write output
        if format.lower() == "json":
            output_content = builder.to_json(spec)
        else:
            output_content = builder.to_yaml(spec)

        with open(output, "w", encoding="utf-8") as f:
            f.write(output_content)

        click.echo(f"✓ Written to {output}")

        # Show warnings if any
        if all_warnings and verbose:
            click.echo("\nWarnings:")
            for warning in all_warnings[:10]:  # Show first 10 warnings
                click.echo(f"  - {warning}")

        # Show errors if any
        if all_errors and verbose:
            click.echo("\nErrors:")
            for error in all_errors[:10]:  # Show first 10 errors
                click.echo(f"  - {error}")

        # Cleanup
        handler.cleanup()

    except KeyboardInterrupt:
        click.echo("\nAborted by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        if verbose:
            import traceback

            click.echo("\nTraceback:", err=True)
            click.echo(traceback.format_exc(), err=True)
        sys.exit(3)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
