"""Integration tests for framework detection."""

from __future__ import annotations

import os
import tempfile

import pytest

from api_extractor.core.detector import FrameworkDetector
from api_extractor.core.models import FrameworkType


class TestFrameworkDetection:
    """Test framework detection logic for each supported framework."""

    # Python Frameworks

    def test_detect_flask(self) -> None:
        """Test detection of Flask framework."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "real-world", "python", "flask", "flask-realworld"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Flask fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.FLASK in frameworks, "Flask should be detected"

    def test_detect_fastapi(self) -> None:
        """Test detection of FastAPI framework."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "real-world", "python", "fastapi", "fastapi-fullstack"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("FastAPI fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.FASTAPI in frameworks, "FastAPI should be detected"

    def test_detect_django_rest(self) -> None:
        """Test detection of Django REST Framework."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "real-world", "python", "django", "django-rest-tutorial"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Django REST fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.DJANGO_REST in frameworks, "Django REST should be detected"

    # JavaScript/TypeScript Frameworks

    def test_detect_express(self) -> None:
        """Test detection of Express framework."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "real-world", "javascript", "express", "express-examples"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Express fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.EXPRESS in frameworks, "Express should be detected"

    def test_detect_nestjs(self) -> None:
        """Test detection of NestJS framework."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "real-world", "javascript", "nestjs", "nestjs-realworld"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("NestJS fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.NESTJS in frameworks, "NestJS should be detected"

    def test_detect_fastify(self) -> None:
        """Test detection of Fastify framework."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "real-world", "javascript", "fastify", "fastify-demo"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Fastify fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.FASTIFY in frameworks, "Fastify should be detected"

    def test_detect_nextjs_app_router(self) -> None:
        """Test detection of Next.js (App Router) via directory structure."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "javascript/nextjs/app"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Next.js App Router fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.NEXTJS in frameworks, "Next.js (App Router) should be detected"

    def test_detect_nextjs_pages_router(self) -> None:
        """Test detection of Next.js (Pages Router) via directory structure."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "javascript/nextjs/pages"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Next.js Pages Router fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.NEXTJS in frameworks, "Next.js (Pages Router) should be detected"

    def test_detect_nextjs_via_package_json(self) -> None:
        """Test detection of Next.js via package.json dependency."""
        # Both app and pages router fixtures have package.json with next dependency
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "javascript/nextjs/app"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Next.js fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        framework_names = {fw.value for fw in frameworks}
        assert "nextjs" in framework_names, "Next.js should be detected via package.json"

    # Java Frameworks

    def test_detect_spring_boot(self) -> None:
        """Test detection of Spring Boot framework."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "java"
        )

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.SPRING_BOOT in frameworks, "Spring Boot should be detected"

    # Edge Cases & Cross-Framework Detection

    def test_detection_failure_empty_directory(self) -> None:
        """Test detection failure on empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FrameworkDetector()
            frameworks = detector.detect(tmpdir)
            assert frameworks is None, "Should not detect any framework in empty directory"

    def test_mixed_framework_detection_python(self) -> None:
        """Test detecting Python frameworks in minimal fixtures (may detect one or more)."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "python"
        )

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        # Should detect at least one Python framework
        assert frameworks is not None
        framework_names = {fw.value for fw in frameworks}

        python_frameworks = framework_names & {"flask", "fastapi", "django_rest"}
        assert len(python_frameworks) >= 1, f"Should detect at least one Python framework, found: {python_frameworks}"

    def test_mixed_framework_detection_javascript(self) -> None:
        """Test detecting JavaScript frameworks in minimal fixtures (may detect one or more)."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "javascript"
        )

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        framework_names = {fw.value for fw in frameworks}

        # Should detect at least one JS framework
        js_frameworks = framework_names & {"express", "nestjs", "fastify"}
        assert len(js_frameworks) >= 1, f"Should detect at least one JS framework, found: {js_frameworks}"

    def test_detection_via_dependencies(self) -> None:
        """Test that detection works from package.json/requirements.txt/pom.xml."""
        # Test with a fixture that has dependency files
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "python"
        )

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        # Should successfully detect via dependencies (Level 1 detection)
        assert frameworks is not None
        assert len(frameworks) > 0, "Should detect frameworks via dependency files"

    def test_detection_via_directory_structure(self) -> None:
        """Test that detection works from directory structure (Next.js specific)."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "javascript/nextjs/app"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Next.js fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        # Next.js can be detected via app/api/ or pages/api/ directory structure
        assert frameworks is not None
        assert FrameworkType.NEXTJS in frameworks, "Should detect Next.js via directory structure"


class TestRealWorldDetection:
    """Test framework detection on real-world projects."""

    def test_detect_nextjs_calcom(self) -> None:
        """Test detection on Cal.com (real-world Next.js)."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "real-world", "javascript", "nextjs", "cal.com"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Cal.com fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.NEXTJS in frameworks, "Should detect Next.js in Cal.com"

    def test_detect_nextjs_dub(self) -> None:
        """Test detection on Dub (real-world Next.js)."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "real-world", "javascript", "nextjs", "dub"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Dub fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.NEXTJS in frameworks, "Should detect Next.js in Dub"

    def test_detect_spring_boot_realworld(self) -> None:
        """Test detection on Spring Boot RealWorld app."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)),
            "..", "..", "fixtures",
            "real-world",
            "java",
            "spring-boot",
            "spring-boot-realworld-example-app",
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Spring Boot RealWorld fixture not available")

        detector = FrameworkDetector()
        frameworks = detector.detect(fixture_dir)

        assert frameworks is not None
        assert FrameworkType.SPRING_BOOT in frameworks, "Should detect Spring Boot in RealWorld app"
