"""Tests for OSC REST API."""
import time


class TestOSCAPI:
    def test_status(self, client):
        resp = client.get("/api/v1/osc/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "listening" in data
        assert "message_count" in data

    def test_send_receive_history_and_clear(self, client):
        start = client.post(
            "/api/v1/osc/listen/start",
            json={"host": "127.0.0.1", "port": 0},
        )
        assert start.status_code == 200
        status = start.json()
        assert status["listening"] is True

        send = client.post(
            "/api/v1/osc/send",
            json={
                "target": {"host": "127.0.0.1", "port": status["port"]},
                "message": {
                    "address": "/netpi/scene",
                    "arguments": [42, "go", True],
                },
            },
        )
        assert send.status_code == 200
        assert send.json()["sent"] is True

        messages = []
        for _ in range(20):
            history = client.get("/api/v1/osc/messages")
            assert history.status_code == 200
            messages = history.json()["messages"]
            if messages:
                break
            time.sleep(0.05)

        assert messages
        assert messages[-1]["address"] == "/netpi/scene"
        assert messages[-1]["arguments"] == [42, "go", True]

        cleared = client.delete("/api/v1/osc/messages")
        assert cleared.status_code == 200
        assert cleared.json()["cleared"] >= 1

        stopped = client.post("/api/v1/osc/listen/stop")
        assert stopped.status_code == 200
        assert stopped.json()["listening"] is False
