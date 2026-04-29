"""CLI interface for API Extractor."""

import sys
import click
from pathlib import Path

from api_extractor.service import ExtractionService
from api_extractor.openapi.builder import OpenAPIBuilder


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
@click.option(
    "--description",
    type=str,
    default=None,
    help="API description for OpenAPI spec",
)
def extract(
    path: str,
    output: str,
    format: str,
    verbose: bool,
    title: str,
    version: str,
    description: str,
):
    """
    Extract API definitions from source code.

    PATH: Path to local codebase directory
    """
    try:
        # Use extraction service
        if verbose:
            click.echo("Starting extraction...")

        service = ExtractionService()
        result = service.extract_api(
            path=path,
            frameworks=None,
            title=title,
            version=version,
            description=description,
        )

        # Check if extraction was successful
        if not result.success:
            click.echo("Error: Extraction failed", err=True)
            if result.errors:
                click.echo("\nErrors encountered:", err=True)
                for error in result.errors[:5]:
                    click.echo(f"  - {error}", err=True)
            sys.exit(3)

        # Show detected frameworks
        if verbose and result.frameworks_detected:
            click.echo("Detected frameworks:")
            for fw in result.frameworks_detected:
                click.echo(f"  ✓ Found: {fw.value}")

        # Show endpoint count
        if verbose:
            click.echo(f"\nExtracted {result.endpoints_count} endpoints")

        # Write output
        builder = OpenAPIBuilder(title=title, version=version, description=description)

        if format.lower() == "json":
            output_content = builder.to_json(result.openapi_spec)
        else:
            output_content = builder.to_yaml(result.openapi_spec)

        with open(output, "w", encoding="utf-8") as f:
            f.write(output_content)

        click.echo(f"✓ Written to {output}")

        # Show warnings if any
        if result.warnings and verbose:
            click.echo("\nWarnings:")
            for warning in result.warnings[:10]:
                click.echo(f"  - {warning}")

        # Show errors if any (non-fatal)
        if result.errors and verbose:
            click.echo("\nNon-fatal errors:")
            for error in result.errors[:10]:
                click.echo(f"  - {error}")

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


@cli.command()
@click.option(
    "--host",
    type=str,
    default="0.0.0.0",
    help="Server host (default: 0.0.0.0)",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=8000,
    help="Server port (default: 8000)",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development",
)
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error"], case_sensitive=False),
    default="info",
    help="Logging level (default: info)",
)
def serve(host: str, port: int, reload: bool, log_level: str):
    """
    Start the API Extractor HTTP server.

    This starts a FastAPI server that exposes HTTP endpoints for
    analyzing codebases and extracting API definitions.
    """
    try:
        import uvicorn
        from api_extractor.server import app

        click.echo("Starting API Extractor HTTP server...")
        click.echo(f"Server: http://{host}:{port}")
        click.echo(f"API Documentation: http://{host}:{port}/docs")
        click.echo(f"ReDoc: http://{host}:{port}/redoc")
        click.echo("\nPress CTRL+C to stop the server\n")

        uvicorn.run(
            "api_extractor.server:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level.lower(),
        )

    except ImportError:
        click.echo(
            "Error: FastAPI dependencies not installed. "
            "Install with: pip install 'api-extractor[server]'",
            err=True,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nServer stopped by user")
    except Exception as e:
        click.echo(f"Error starting server: {str(e)}", err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
