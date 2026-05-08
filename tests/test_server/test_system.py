"""Tests for system endpoints."""
import pytest


class TestRoot:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "NetPi"
        assert data["status"] == "ok"
        assert "features" in data


class TestHealth:
    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_ready(self, client):
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ready", "not_ready")
        assert "checks" in data


class TestMetrics:
    def test_metrics(self, client):
        # Make a request first to populate metrics
        client.get("/")
        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "netpi_requests_total" in data
        assert "netpi_errors_total" in data



