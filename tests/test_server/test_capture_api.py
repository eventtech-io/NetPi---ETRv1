"""Tests for capture REST API."""
import pytest


class TestCaptureEndpoints:
    def test_start_capture(self, client, mock_capture_engine):
        from netpi_core.models.capture import CaptureFilter
        resp = client.post("/api/v1/capture/start", json={
            "interface": "lo",
            "max_packets": 10,
            "promiscuous": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert "id" in data

    def test_stop_capture(self, client, mock_capture_engine):
        # Start then stop
        start = client.post("/api/v1/capture/start", json={"interface": "lo"})
        sid = start.json()["id"]

        resp = client.post(f"/api/v1/capture/{sid}/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

    def test_get_capture(self, client, mock_capture_engine):
        start = client.post("/api/v1/capture/start", json={"interface": "lo"})
        sid = start.json()["id"]

        resp = client.get(f"/api/v1/capture/{sid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sid

    def test_list_captures(self, client, mock_capture_engine):
        resp = client.get("/api/v1/capture")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_download_not_found(self, client):
        resp = client.get("/api/v1/capture/nonexistent/download")
        assert resp.status_code == 404

    def test_bpf_sanitization(self, client, mock_capture_engine):
        resp = client.post("/api/v1/capture/start", json={
            "interface": "lo",
            "bpf_expression": "port 80; rm -rf /",
        })
        assert resp.status_code == 422
        assert "Disallowed" in resp.json()["detail"]


class TestCaptureAuth:
    def test_capture_requires_auth(self, client_with_auth):
        resp = client_with_auth.post("/api/v1/capture/start", json={"interface": "lo"})
        assert resp.status_code == 401



