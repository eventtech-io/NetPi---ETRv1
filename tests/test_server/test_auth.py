"""Tests for API key authentication."""
import pytest


class TestAuthDisabled:
    def test_no_key_required(self, client):
        resp = client.get("/api/v1/system/info")
        assert resp.status_code == 200


class TestAuthEnabled:
    def test_missing_key(self, client_with_auth):
        resp = client_with_auth.get("/api/v1/system/info")
        assert resp.status_code == 401
        assert "API key" in resp.json()["detail"]

    def test_wrong_key(self, client_with_auth):
        resp = client_with_auth.get(
            "/api/v1/system/info",
            headers={"X-API-Key": "wrong-key"}
        )
        assert resp.status_code == 401

    def test_valid_key(self, client_with_auth):
        resp = client_with_auth.get(
            "/api/v1/system/info",
            headers={"X-API-Key": "test-secret-key"}
        )
        assert resp.status_code == 200

    def test_health_open(self, client_with_auth):
        resp = client_with_auth.get("/api/v1/health")
        assert resp.status_code == 200

    def test_metrics_open(self, client_with_auth):
        resp = client_with_auth.get("/api/v1/metrics")
        assert resp.status_code == 200



