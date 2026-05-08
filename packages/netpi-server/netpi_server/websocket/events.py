"""WebSocket event hub."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# BUG-FIX: was named 'router' but every import site expected 'ws_router'
ws_router = APIRouter(tags=["websocket"])


@ws_router.websocket("/ws/events")
async def events_websocket(websocket: WebSocket):
    """General event WebSocket — echoes messages, will broadcast system events."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"echo": data})
    except WebSocketDisconnect:
        pass
