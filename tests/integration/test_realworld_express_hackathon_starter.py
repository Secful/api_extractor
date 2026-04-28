"""Integration tests for Express extractor with hackathon-starter."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.javascript.express import ExpressExtractor


@pytest.fixture
def hackathon_starter_path():
    """Get path to hackathon-starter fixture."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "javascript",
        "express",
        "hackathon-starter",
    )
    if not os.path.exists(path):
        pytest.skip("Hackathon Starter fixture not available (run: git submodule update --init)")
    return path


class TestExpressHackathonStarter:
    """Integration tests for hackathon-starter boilerplate."""

    def test_extraction(self, hackathon_starter_path: str) -> None:
        """Test extraction from hackathon-starter.

        Repository: https://github.com/sahat/hackathon-starter
        Domain: Multi-Service Integration Hub / Boilerplate
        """
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count (exact match per coding standards)
        assert len(result.endpoints) == 108, \
            f"Expected exactly 108 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, hackathon_starter_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"

    def test_authentication_endpoints(self, hackathon_starter_path: str) -> None:
        """Test that core authentication endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Core auth endpoints
        assert "/login" in paths, "Should find login endpoint"
        assert "/signup" in paths, "Should find signup endpoint"
        assert "/logout" in paths, "Should find logout endpoint"
        assert "/account" in paths, "Should find account management endpoint"

    def test_oauth_endpoints(self, hackathon_starter_path: str) -> None:
        """Test that OAuth provider endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find OAuth-related endpoints
        oauth_endpoints = [ep for ep in result.endpoints
                          if "auth" in ep.path and ("google" in ep.path or "github" in ep.path
                                                    or "facebook" in ep.path or "instagram" in ep.path)]
        assert len(oauth_endpoints) == 6, \
            f"Expected exactly 6 OAuth endpoints, found {len(oauth_endpoints)}"

    def test_two_factor_auth(self, hackathon_starter_path: str) -> None:
        """Test that 2FA endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find 2FA endpoints
        tfa_endpoints = [ep for ep in result.endpoints if "2fa" in ep.path or "totp" in ep.path]
        assert len(tfa_endpoints) == 10, \
            f"Expected exactly 10 2FA endpoints, found {len(tfa_endpoints)}"

        # Verify specific 2FA patterns
        paths = {ep.path for ep in result.endpoints}
        assert any("totp/setup" in p for p in paths), "Should find TOTP setup endpoint"

    def test_webauthn_endpoints(self, hackathon_starter_path: str) -> None:
        """Test that WebAuthn/passwordless endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find WebAuthn endpoints
        webauthn_endpoints = [ep for ep in result.endpoints if "webauthn" in ep.path]
        assert len(webauthn_endpoints) == 7, \
            f"Expected exactly 7 WebAuthn endpoints, found {len(webauthn_endpoints)}"

    def test_payment_endpoints(self, hackathon_starter_path: str) -> None:
        """Test that payment processing endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find payment endpoints
        payment_endpoints = [ep for ep in result.endpoints
                            if "stripe" in ep.path or "paypal" in ep.path]
        assert len(payment_endpoints) >= 4, \
            f"Expected at least 4 payment endpoints, found {len(payment_endpoints)}"

    def test_api_integration_endpoints(self, hackathon_starter_path: str) -> None:
        """Test that /api/* third-party integration endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find /api/* endpoints
        api_endpoints = [ep for ep in result.endpoints if ep.path.startswith("/api/")]
        assert len(api_endpoints) == 29, \
            f"Expected exactly 29 /api/* endpoints, found {len(api_endpoints)}"

    def test_ai_ml_endpoints(self, hackathon_starter_path: str) -> None:
        """Test that AI/ML feature endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find AI/ML endpoints
        ai_endpoints = [ep for ep in result.endpoints if "/ai" in ep.path]
        assert len(ai_endpoints) == 13, \
            f"Expected exactly 13 AI/ML endpoints, found {len(ai_endpoints)}"

        # Verify specific AI patterns
        paths = {ep.path for ep in result.endpoints}
        assert any("rag" in p for p in paths), "Should find RAG endpoint"
        assert any("llm" in p for p in paths), "Should find LLM endpoint"
        assert any("ai-agent" in p for p in paths), "Should find AI agent endpoint"

    def test_account_management_endpoints(self, hackathon_starter_path: str) -> None:
        """Test that account management endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find account management endpoints
        account_endpoints = [ep for ep in result.endpoints if "/account" in ep.path]
        assert len(account_endpoints) == 17, \
            f"Expected exactly 17 account management endpoints, found {len(account_endpoints)}"

        # Verify specific account patterns
        paths = {ep.path for ep in result.endpoints}
        assert "/account/profile" in paths, "Should find profile update endpoint"
        assert "/account/password" in paths, "Should find password change endpoint"
        assert "/account/delete" in paths, "Should find account deletion endpoint"

    def test_path_parameters(self, hackathon_starter_path: str) -> None:
        """Test that path parameters are properly extracted in OpenAPI format."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) == 5, \
            f"Expected exactly 5 endpoints with path parameters, found {len(param_endpoints)}"

        # Verify OpenAPI format (not Express :param format)
        for ep in param_endpoints:
            assert "{" in ep.path and "}" in ep.path, \
                f"Path parameter should use OpenAPI format: {ep.path}"
            assert ":" not in ep.path, \
                f"Path should not contain Express :param format: {ep.path}"

        # Verify specific parameter patterns
        paths = {ep.path for ep in result.endpoints}
        assert any("{provider}" in p for p in paths), "Should find {provider} parameter"
        assert any("{token}" in p for p in paths), "Should find {token} parameter"

    def test_source_tracking(self, hackathon_starter_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith(".js"), \
                f"Expected .js file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert ep.source_line > 0, f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_password_reset_flow(self, hackathon_starter_path: str) -> None:
        """Test that password reset flow endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find password reset endpoints
        reset_endpoints = [ep for ep in result.endpoints if "reset" in ep.path or "forgot" in ep.path]
        assert len(reset_endpoints) >= 3, \
            f"Expected at least 3 password reset endpoints, found {len(reset_endpoints)}"

    def test_contact_endpoints(self, hackathon_starter_path: str) -> None:
        """Test that contact form endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        paths = {ep.path for ep in result.endpoints}
        assert "/contact" in paths, "Should find contact endpoint"

    def test_multiple_methods_per_path(self, hackathon_starter_path: str) -> None:
        """Test that paths with multiple HTTP methods are correctly extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Group endpoints by path
        path_methods = {}
        for ep in result.endpoints:
            if ep.path not in path_methods:
                path_methods[ep.path] = set()
            path_methods[ep.path].add(ep.method)

        # Find paths with multiple methods
        multi_method_paths = [p for p, methods in path_methods.items() if len(methods) > 1]
        assert len(multi_method_paths) == 16, \
            f"Expected exactly 16 paths with multiple HTTP methods, found {len(multi_method_paths)}"

    def test_unique_paths(self, hackathon_starter_path: str) -> None:
        """Test that correct number of unique paths are found."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        unique_paths = set(ep.path for ep in result.endpoints)
        assert len(unique_paths) == 90, \
            f"Expected exactly 90 unique paths, found {len(unique_paths)}"

    def test_file_upload_endpoints(self, hackathon_starter_path: str) -> None:
        """Test that file upload endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(hackathon_starter_path)

        assert result.success

        # Find upload endpoints
        upload_endpoints = [ep for ep in result.endpoints if "upload" in ep.path]
        assert len(upload_endpoints) >= 1, \
            f"Expected at least 1 upload endpoint, found {len(upload_endpoints)}"
