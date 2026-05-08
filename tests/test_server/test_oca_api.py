"""Tests for OCA/AES70 REST API."""


class TestOCAAPI:
    def test_status_and_classes(self, client):
        status = client.get("/api/v1/oca/status")
        assert status.status_code == 200
        assert status.json()["implementation"] == "discovery_registry_tcp_probe"

        classes = client.get("/api/v1/oca/classes")
        assert classes.status_code == 200
        assert any(item["name"] == "OcaRoot" for item in classes.json())

    def test_manual_device_lifecycle(self, client):
        created = client.post(
            "/api/v1/oca/devices",
            json={"name": "Stage Processor", "host": "127.0.0.1", "port": 65000},
        )
        assert created.status_code == 200
        device = created.json()
        device_id = device["id"]
        assert device["source"] == "manual"

        fetched = client.get(f"/api/v1/oca/devices/{device_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Stage Processor"

        objects = client.get(f"/api/v1/oca/devices/{device_id}/objects")
        assert objects.status_code == 200
        assert objects.json()["objects"][0]["class_name"] == "OcaRoot"

        probe = client.post(f"/api/v1/oca/devices/{device_id}/probe", params={"timeout_sec": 0.2})
        assert probe.status_code == 200
        assert "reachable" in probe.json()

        deleted = client.delete(f"/api/v1/oca/devices/{device_id}")
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True

    def test_discovery_endpoint_no_hardware_safe(self, client):
        resp = client.post(
            "/api/v1/oca/discover",
            json={"timeout_sec": 0.1, "service_type": "_oca._tcp.local."},
        )
        assert resp.status_code == 200
        assert "devices" in resp.json()
        assert "count" in resp.json()
