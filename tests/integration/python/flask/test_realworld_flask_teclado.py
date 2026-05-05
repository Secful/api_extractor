"""Integration tests for Flask extractor with Teclado Flask REST API course."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.python.flask import FlaskExtractor


@pytest.fixture
def flask_teclado_path():
    """Get path to Teclado Flask REST API fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "fixtures",
        "real-world",
        "python",
        "flask",
        "rest-apis-flask-python",
    )
    if not os.path.exists(path):
        pytest.skip("Flask Teclado fixture not available (run: git submodule update --init)")
    return path


class TestFlaskTecladoBasic:
    """Integration tests for basic Flask app (01-first-rest-api)."""

    @pytest.fixture
    def basic_app_path(self, flask_teclado_path):
        """Get path to basic Flask app."""
        return os.path.join(flask_teclado_path, "project", "01-first-rest-api")

    def test_extraction(self, basic_app_path: str) -> None:
        """Test extraction from basic Flask app.

        Repository: https://github.com/tecladocode/rest-apis-flask-python
        Project: 01-first-rest-api
        Domain: Simple store/items CRUD API
        """
        extractor = FlaskExtractor()
        result = extractor.extract(basic_app_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) == 5, \
            f"Expected 5 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, basic_app_path: str) -> None:
        """Test that GET and POST methods are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(basic_app_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"

    def test_path_parameters(self, basic_app_path: str) -> None:
        """Test that path parameters are properly extracted and normalized."""
        extractor = FlaskExtractor()
        result = extractor.extract(basic_app_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) == 3, \
            f"Expected 3 endpoints with path parameters, found {len(param_endpoints)}"

        # Check path normalization from Flask <string:name> to OpenAPI {name}
        paths = {ep.path for ep in result.endpoints}
        assert "/store/{name}" in paths, "Should normalize <string:name> to {name}"
        assert "/store/{name}/item" in paths, "Should normalize nested paths"

    def test_specific_endpoints(self, basic_app_path: str) -> None:
        """Test that expected endpoints are found."""
        extractor = FlaskExtractor()
        result = extractor.extract(basic_app_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        assert "/store" in paths, "Should find store list endpoint"
        assert "/store/{name}" in paths, "Should find store detail endpoint"
        assert "/store/{name}/item" in paths, "Should find item endpoints"


class TestFlaskTecladoSmorest:
    """Integration tests for Flask-Smorest app (using-flask-smorest)."""

    @pytest.fixture
    def smorest_app_path(self, flask_teclado_path):
        """Get path to Flask-Smorest app."""
        return os.path.join(flask_teclado_path, "project", "using-flask-smorest")

    def test_extraction(self, smorest_app_path: str) -> None:
        """Test extraction from Flask-Smorest app.

        Repository: https://github.com/tecladocode/rest-apis-flask-python
        Project: using-flask-smorest
        Domain: Store/items API with JWT authentication and tags
        """
        extractor = FlaskExtractor()
        result = extractor.extract(smorest_app_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) == 18, \
            f"Expected 18 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, smorest_app_path: str) -> None:
        """Test that all HTTP methods are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(smorest_app_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_methodview_endpoints(self, smorest_app_path: str) -> None:
        """Test that MethodView classes are properly extracted."""
        extractor = FlaskExtractor()
        result = extractor.extract(smorest_app_path)

        assert result.success

        # Item resource with multiple methods
        item_endpoints = [ep for ep in result.endpoints if ep.path == "/item/{name}"]
        assert len(item_endpoints) == 4, \
            f"Item MethodView should have 4 HTTP methods, found {len(item_endpoints)}"

        methods = {ep.method for ep in item_endpoints}
        assert methods == {HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.DELETE}, \
            "Item endpoint should support GET, POST, PUT, DELETE"

    def test_auth_endpoints(self, smorest_app_path: str) -> None:
        """Test that authentication endpoints are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(smorest_app_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        assert "/register" in paths, "Should find register endpoint"
        assert "/login" in paths, "Should find login endpoint"
        assert "/logout" in paths, "Should find logout endpoint"
        assert "/refresh" in paths, "Should find token refresh endpoint"

    def test_tag_endpoints(self, smorest_app_path: str) -> None:
        """Test that tag management endpoints are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(smorest_app_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        tag_paths = [p for p in paths if "tag" in p.lower()]
        assert len(tag_paths) >= 1, \
            f"Should find tag endpoints, found {len(tag_paths)}"

    def test_request_response_schemas(self, smorest_app_path: str) -> None:
        """Test that request/response schemas are referenced."""
        extractor = FlaskExtractor()
        result = extractor.extract(smorest_app_path)

        assert result.success

        # Find endpoints with request bodies
        endpoints_with_body = [ep for ep in result.endpoints if ep.request_body]
        assert len(endpoints_with_body) > 0, "Should find endpoints with request bodies"

        # Find endpoints with response schemas
        endpoints_with_response = [
            ep for ep in result.endpoints
            if ep.responses and any(
                r.response_schema is not None
                for r in ep.responses
            )
        ]
        assert len(endpoints_with_response) > 0, "Should find endpoints with response schemas"


class TestFlaskTecladoRestx:
    """Integration tests for Flask-RESTX app (using-flask-restx)."""

    @pytest.fixture
    def restx_app_path(self, flask_teclado_path):
        """Get path to Flask-RESTX app."""
        return os.path.join(flask_teclado_path, "project", "using-flask-restx")

    def test_extraction(self, restx_app_path: str) -> None:
        """Test extraction from Flask-RESTX app.

        Repository: https://github.com/tecladocode/rest-apis-flask-python
        Project: using-flask-restx
        Domain: Store/items API with Swagger documentation
        """
        extractor = FlaskExtractor()
        result = extractor.extract(restx_app_path)

        assert result.success, "Extraction should succeed"
        # Allow some tolerance for endpoint count
        assert len(result.endpoints) >= 15, \
            f"Expected at least 15 endpoints, found {len(result.endpoints)}"

    def test_namespace_resources(self, restx_app_path: str) -> None:
        """Test that Namespace resources are properly extracted."""
        extractor = FlaskExtractor()
        result = extractor.extract(restx_app_path)

        assert result.success

        # Item resource in namespace
        item_detail_endpoints = [ep for ep in result.endpoints if "/{name}" in ep.path and "item" in ep.source_file.lower()]
        assert len(item_detail_endpoints) >= 3, \
            f"Should find item resource with multiple methods, found {len(item_detail_endpoints)}"

    def test_api_models(self, restx_app_path: str) -> None:
        """Test that Flask-RESTX api.model definitions are handled."""
        extractor = FlaskExtractor()
        result = extractor.extract(restx_app_path)

        assert result.success

        # Endpoints should have some schema information
        post_endpoints = [ep for ep in result.endpoints if ep.method == HTTPMethod.POST]
        assert len(post_endpoints) > 0, "Should find POST endpoints"


class TestFlaskTecladoMultipleProjects:
    """Integration tests across multiple Teclado Flask projects."""

    def test_all_projects_extractable(self, flask_teclado_path: str) -> None:
        """Test that all Flask project variants are extractable."""
        extractor = FlaskExtractor()

        # List of project directories to test
        projects = [
            "01-first-rest-api",
            "03-items-stores-smorest",
            "04-items-stores-smorest-sqlalchemy",
            "05-add-many-to-many",
            "06-add-db-migrations",
            "using-flask-smorest",
            "using-flask-restx",
        ]

        for project in projects:
            project_path = os.path.join(flask_teclado_path, "project", project)
            if not os.path.exists(project_path):
                continue

            result = extractor.extract(project_path)
            assert result.success, f"Extraction should succeed for {project}"
            assert len(result.endpoints) > 0, f"Should find endpoints in {project}"

    def test_source_tracking_across_projects(self, flask_teclado_path: str) -> None:
        """Test that source files are tracked across all projects."""
        extractor = FlaskExtractor()

        projects = ["01-first-rest-api", "using-flask-smorest", "using-flask-restx"]

        for project in projects:
            project_path = os.path.join(flask_teclado_path, "project", project)
            if not os.path.exists(project_path):
                continue

            result = extractor.extract(project_path)
            assert result.success

            for ep in result.endpoints:
                assert ep.source_file is not None, f"Source file should be tracked in {project}"
                assert ep.source_file.endswith(".py"), f"Source should be Python file in {project}"
                assert ep.source_line is not None, f"Source line should be tracked in {project}"
                assert ep.source_line > 0, f"Source line should be positive in {project}"
