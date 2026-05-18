"""Integration test: Generate OpenAPI specs for all real-world fixtures."""

import yaml
from pathlib import Path

import pytest

from api_extractor.core.detector import FrameworkDetector
from api_extractor.core.models import FrameworkType
from api_extractor.extractors.python.fastapi import FastAPIExtractor
from api_extractor.extractors.python.flask import FlaskExtractor
from api_extractor.extractors.python.django_rest import DjangoRESTExtractor
from api_extractor.extractors.javascript.express import ExpressExtractor
from api_extractor.extractors.javascript.express_zod_api import ExpressZodAPIExtractor
from api_extractor.extractors.javascript.nestjs import NestJSExtractor
from api_extractor.extractors.javascript.fastify import FastifyExtractor
from api_extractor.extractors.javascript.nextjs import NextJSExtractor
from api_extractor.extractors.go.gin import GinExtractor
from api_extractor.extractors.java.spring_boot import SpringBootExtractor
from api_extractor.extractors.csharp.aspnet_core import ASPNETCoreExtractor
from api_extractor.openapi.builder import OpenAPIBuilder


def get_extractor(framework: FrameworkType):
    """Get extractor instance for framework."""
    extractors = {
        FrameworkType.FASTAPI: FastAPIExtractor,
        FrameworkType.FLASK: FlaskExtractor,
        FrameworkType.DJANGO_REST: DjangoRESTExtractor,
        FrameworkType.EXPRESS: ExpressExtractor,
        FrameworkType.EXPRESS_ZOD_API: ExpressZodAPIExtractor,
        FrameworkType.NESTJS: NestJSExtractor,
        FrameworkType.FASTIFY: FastifyExtractor,
        FrameworkType.NEXTJS: NextJSExtractor,
        FrameworkType.GIN: GinExtractor,
        FrameworkType.SPRING_BOOT: SpringBootExtractor,
        FrameworkType.ASPNET_CORE: ASPNETCoreExtractor,
    }
    extractor_class = extractors.get(framework)
    return extractor_class() if extractor_class else None


# Fixture mapping: (path_suffix, output_name, framework_hint)
FIXTURES = [
    # Python FastAPI
    ("python/fastapi/polar/server", "fastapi-polar", None),
    ("python/fastapi/fastapi-fullstack", "fastapi-fullstack", None),
    ("python/fastapi/docflow", "fastapi-docflow", None),
    ("python/fastapi/autogpt", "fastapi-autogpt", None),

    # Python Flask
    ("python/flask/flask-realworld", "flask-realworld", None),
    ("python/flask/rest-apis-flask-python", "flask-rest-apis", None),
    ("python/flask/mentorship-backend", "flask-mentorship", None),

    # Python Django
    ("python/django/django-rest-tutorial", "django-rest-tutorial", None),

    # JavaScript Express
    ("javascript/express/acquisitions", "express-acquisitions", None),
    ("javascript/express/node-express-boilerplate", "express-boilerplate", None),
    ("javascript/express/express-zod-api/example", "express-zod-api", FrameworkType.EXPRESS_ZOD_API),

    # JavaScript NestJS
    ("javascript/nestjs/nestjs-realworld", "nestjs-realworld", None),
    ("javascript/nestjs/twenty", "nestjs-twenty", None),

    # JavaScript Fastify
    ("javascript/fastify/fastify-demo", "fastify-demo", None),
    ("javascript/fastify/fastify-example", "fastify-example", None),

    # JavaScript Next.js
    ("javascript/nextjs/inbox-zero/apps/web", "nextjs-inbox-zero", None),

    # Go Gin
    ("go/gin/golang-gin-realworld-example-app", "gin-realworld", None),

    # Java Spring Boot
    ("java/spring-boot/spring-boot-realworld-example-app", "spring-boot-realworld", None),

    # C# ASP.NET Core
    ("csharp/aspnet-core/aspnetcore-realworld-example-app/src", "aspnet-core-realworld", None),
]


@pytest.fixture
def output_dir():
    """Create output directory for OpenAPI specs."""
    output = Path("/tmp/api-extractor-openapi-specs")
    output.mkdir(exist_ok=True)
    return output


class TestGenerateOpenAPISpecs:
    """Generate OpenAPI YAML files for all fixtures."""

    @pytest.mark.parametrize("fixture_path,output_name,framework_hint", FIXTURES)
    def test_generate_openapi_spec(
        self,
        fixture_path: str,
        output_name: str,
        framework_hint: str | None,
        output_dir: Path,
    ) -> None:
        """Generate OpenAPI spec for a single fixture.

        Args:
            fixture_path: Relative path from fixtures/real-world/
            output_name: Output filename (without .yaml)
            framework_hint: Optional framework override
            output_dir: Output directory
        """
        # Build full path
        fixtures_base = Path(__file__).parent.parent / "fixtures" / "real-world"
        full_path = fixtures_base / fixture_path

        if not full_path.exists():
            pytest.skip(f"Fixture not found: {full_path}")

        # Detect framework
        if framework_hint:
            framework = framework_hint
        else:
            detector = FrameworkDetector()
            frameworks = detector.detect(str(full_path))
            if not frameworks:
                pytest.skip(f"No framework detected for {fixture_path}")
            framework = frameworks[0]

        # Extract endpoints
        extractor = get_extractor(framework)
        if not extractor:
            pytest.skip(f"No extractor for framework: {framework}")

        result = extractor.extract(str(full_path))

        if not result.success:
            pytest.skip(f"Extraction failed: {'; '.join(result.errors)}")

        if not result.endpoints:
            pytest.skip("No endpoints extracted")

        # Build OpenAPI spec
        builder = OpenAPIBuilder(
            title=f"{output_name} API",
            version="1.0.0",
            description=f"Auto-generated from {fixture_path}",
        )
        spec = builder.build(result.endpoints)

        # Convert to dict and write YAML
        spec_dict = spec.model_dump(exclude_none=True, by_alias=True)

        output_file = output_dir / f"{output_name}.yaml"
        with open(output_file, "w") as f:
            yaml.dump(spec_dict, f, sort_keys=False, default_flow_style=False)

        # Verify file created
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Log success
        print(f"\n✓ Generated: {output_file}")
        print(f"  Endpoints: {len(result.endpoints)}")
        print(f"  Paths: {len(spec_dict.get('paths', {}))}")


def test_list_generated_specs(output_dir: Path) -> None:
    """List all generated OpenAPI specs at the end."""
    specs = sorted(output_dir.glob("*.yaml"))

    if not specs:
        pytest.skip("No specs generated yet")

    print(f"\n{'='*60}")
    print(f"Generated {len(specs)} OpenAPI specifications:")
    print(f"{'='*60}")

    for spec_file in specs:
        size_kb = spec_file.stat().st_size / 1024
        print(f"  {spec_file.name:<40} {size_kb:>8.1f} KB")

    print(f"\nOutput directory: {output_dir}")
    print(f"{'='*60}\n")
