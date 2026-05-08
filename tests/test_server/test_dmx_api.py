"""Tests for DMX REST API."""
import pytest


class TestDMXUniverseAPI:
    def test_create_universe(self, client):
        resp = client.post("/api/v1/dmx/universes", params={"name": "Test Uni"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Uni"
        assert len(data["channels"]) == 512

    def test_list_universes(self, client):
        client.post("/api/v1/dmx/universes", params={"name": "U1"})
        resp = client.get("/api/v1/dmx/universes")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_universe(self, client):
        created = client.post("/api/v1/dmx/universes", params={"name": "U2"})
        uid = created.json()["id"]
        resp = client.get(f"/api/v1/dmx/universes/{uid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == uid

    def test_get_universe_not_found(self, client):
        resp = client.get("/api/v1/dmx/universes/fake-id")
        assert resp.status_code == 404

    def test_set_channel(self, client):
        created = client.post("/api/v1/dmx/universes", params={"name": "U3"})
        uid = created.json()["id"]
        resp = client.post(f"/api/v1/dmx/universes/{uid}/channels/10", params={"value": 128})
        assert resp.status_code == 200
        assert resp.json()["value"] == 128

    def test_set_channel_invalid(self, client):
        resp = client.post("/api/v1/dmx/universes/fake/channels/10", params={"value": 128})
        assert resp.status_code == 404


class TestDMXTransmissionAPI:
    @pytest.mark.asyncio
    async def test_start_transmit(self, client):
        created = client.post("/api/v1/dmx/universes", params={"name": "TX Test"})
        uid = created.json()["id"]
        resp = client.post(f"/api/v1/dmx/universes/{uid}/transmit/start", params={"rate_hz": 44.0})
        assert resp.status_code == 200
        assert resp.json()["status"] == "transmitting"

        # Cleanup
        client.post(f"/api/v1/dmx/universes/{uid}/transmit/stop")

    def test_stop_transmit(self, client):
        created = client.post("/api/v1/dmx/universes", params={"name": "TX Stop"})
        uid = created.json()["id"]
        client.post(f"/api/v1/dmx/universes/{uid}/transmit/start")
        resp = client.post(f"/api/v1/dmx/universes/{uid}/transmit/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"


class TestDMXFixtureAPI:
    def test_add_fixture(self, client):
        created = client.post("/api/v1/dmx/universes", params={"name": "Fixture Test"})
        uid = created.json()["id"]
        resp = client.post(
            f"/api/v1/dmx/universes/{uid}/fixtures",
            params={"profile_id": "generic_rgb", "start_address": 1, "mode": "3ch"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Generic RGB @ 1"
        assert data["channel_count"] == 3

    def test_add_fixture_invalid_profile(self, client):
        created = client.post("/api/v1/dmx/universes", params={"name": "Bad Fixture"})
        uid = created.json()["id"]
        resp = client.post(
            f"/api/v1/dmx/universes/{uid}/fixtures",
            params={"profile_id": "nonexistent", "start_address": 1}
        )
        assert resp.status_code == 404


class TestDIPSwitch:
    def test_dip_switch_valid(self, client):
        resp = client.get("/api/v1/dmx/dip-switch/257")
        assert resp.status_code == 200
        assert resp.json()["address"] == 257

    def test_dip_switch_invalid(self, client):
        resp = client.get("/api/v1/dmx/dip-switch/0")
        assert resp.status_code == 422

        resp = client.get("/api/v1/dmx/dip-switch/513")
        assert resp.status_code == 422



