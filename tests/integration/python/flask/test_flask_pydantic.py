"""Integration test for flask-pydantic support."""
from pathlib import Path
import pytest
from api_extractor.extractors.python.flask import FlaskExtractor
from api_extractor.core.models import HTTPMethod, ParameterLocation


class TestFlaskPydanticIntegration:
    """Test flask-pydantic real-world example."""

    @pytest.fixture
    def extractor(self):
        return FlaskExtractor()

    @pytest.fixture
    def result(self, extractor):
        # Get path relative to this test file
        test_dir = Path(__file__).parent.parent.parent.parent
        fixture_path = test_dir / "fixtures" / "real-world" / "python" / "flask" / "flask-pydantic" / "example_app"
        return extractor.extract(str(fixture_path))

    def test_total_endpoints(self, result):
        """Should extract all endpoints from both example.py and app.py."""
        assert len(result.endpoints) == 11
        assert len(result.errors) == 0

    def test_get_with_query_params(self, result):
        """GET / with query parameters from QueryModel."""
        endpoints = [
            ep for ep in result.endpoints
            if ep.path == "/" and ep.method == HTTPMethod.GET
        ]
        assert len(endpoints) == 1
        
        ep = endpoints[0]
        query_params = [p for p in ep.parameters if p.location == ParameterLocation.QUERY]
        assert len(query_params) == 1
        assert query_params[0].name == "age"
        assert query_params[0].type == "integer"
        assert query_params[0].required is True

    def test_get_with_path_param(self, result):
        """GET /character/{character_id}/ with path parameter."""
        endpoints = [
            ep for ep in result.endpoints
            if "/character/" in ep.path and ep.method == HTTPMethod.GET
        ]
        assert len(endpoints) == 1
        
        ep = endpoints[0]
        path_params = [p for p in ep.parameters if p.location == ParameterLocation.PATH]
        assert len(path_params) == 1
        assert path_params[0].name == "character_id"
        assert path_params[0].required is True

    def test_post_with_body_kwarg(self, result):
        """POST / with body parameter (example.py)."""
        endpoints = [
            ep for ep in result.endpoints
            if ep.path == "/" and ep.method == HTTPMethod.POST and "example.py" in ep.source_file
        ]
        assert len(endpoints) == 1
        
        ep = endpoints[0]
        assert ep.request_body is not None
        assert ep.request_body.type == "object"
        assert "name" in ep.request_body.properties
        assert "nickname" in ep.request_body.properties
        assert ep.request_body.properties["name"]["type"] == "string"
        assert "name" in ep.request_body.required

    def test_post_with_decorator_args(self, result):
        """POST / with @validate(body=Model, query=Model) decorator args."""
        endpoints = [
            ep for ep in result.endpoints
            if ep.path == "/" and ep.method == HTTPMethod.POST and "app.py" in ep.source_file
        ]
        assert len(endpoints) == 1
        
        ep = endpoints[0]
        
        # Body from decorator
        assert ep.request_body is not None
        assert "name" in ep.request_body.properties
        assert "nickname" in ep.request_body.properties
        
        # Query params from decorator
        query_params = [p for p in ep.parameters if p.location == ParameterLocation.QUERY]
        assert len(query_params) == 1
        assert query_params[0].name == "age"
        assert query_params[0].type == "integer"

    def test_post_with_form_data(self, result):
        """POST /form with form data parameter."""
        endpoints = [
            ep for ep in result.endpoints
            if ep.path == "/form" and ep.method == HTTPMethod.POST and "example.py" in ep.source_file
        ]
        assert len(endpoints) == 1
        
        ep = endpoints[0]
        assert ep.request_body is not None
        assert "name" in ep.request_body.properties
        assert "nickname" in ep.request_body.properties

    def test_post_with_both_body_and_query(self, result):
        """POST /both with both body and query parameters."""
        endpoints = [
            ep for ep in result.endpoints
            if ep.path == "/both" and ep.method == HTTPMethod.POST
        ]
        assert len(endpoints) == 1
        
        ep = endpoints[0]
        
        # Body
        assert ep.request_body is not None
        assert "name" in ep.request_body.properties
        
        # Query
        query_params = [p for p in ep.parameters if p.location == ParameterLocation.QUERY]
        assert len(query_params) == 1
        assert query_params[0].name == "age"

    def test_kwargs_pattern(self, result):
        """POST /kwargs using function kwargs pattern."""
        endpoints = [
            ep for ep in result.endpoints
            if ep.path == "/kwargs" and ep.method == HTTPMethod.POST
        ]
        assert len(endpoints) == 1
        
        ep = endpoints[0]
        assert ep.request_body is not None
        query_params = [p for p in ep.parameters if p.location == ParameterLocation.QUERY]
        assert len(query_params) == 1

    def test_form_kwargs_pattern(self, result):
        """POST /form/kwargs using form kwargs pattern."""
        endpoints = [
            ep for ep in result.endpoints
            if ep.path == "/form/kwargs" and ep.method == HTTPMethod.POST
        ]
        assert len(endpoints) == 1
        
        ep = endpoints[0]
        assert ep.request_body is not None
        query_params = [p for p in ep.parameters if p.location == ParameterLocation.QUERY]
        assert len(query_params) == 1

    def test_many_response(self, result):
        """GET /many with response_many=True."""
        endpoints = [
            ep for ep in result.endpoints
            if ep.path == "/many" and ep.method == HTTPMethod.GET
        ]
        assert len(endpoints) == 1

    def test_select_with_array_body(self, result):
        """POST /select with request_body_many=True."""
        endpoints = [
            ep for ep in result.endpoints
            if ep.path == "/select" and ep.method == HTTPMethod.POST
        ]
        assert len(endpoints) == 1
        
        ep = endpoints[0]
        assert ep.request_body is not None
        query_params = [p for p in ep.parameters if p.location == ParameterLocation.QUERY]
        assert len(query_params) == 1
        assert query_params[0].name == "index"
