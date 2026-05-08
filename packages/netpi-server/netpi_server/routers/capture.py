"""Packet capture endpoints."""
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from netpi_core.config import get_settings
from netpi_core.models.capture import CaptureFilter
from netpi_analyzer.capture.engine import get_engine
from netpi_analyzer.capture.validation import ValidationError, sanitize_bpf, validate_capture_path

router = APIRouter(tags=["capture"])
logger = logging.getLogger("netpi.capture")


@router.post("/capture/start")
async def start_capture(filter_cfg: CaptureFilter):
    if filter_cfg.bpf_expression:
        try:
            sanitize_bpf(filter_cfg.bpf_expression)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    try:
        return await get_engine().start(filter_cfg)
    except Exception as exc:
        logger.exception("Failed to start capture")
        raise HTTPException(status_code=500, detail=f"Capture start failed: {exc}")


@router.post("/capture/{session_id}/stop")
async def stop_capture(session_id: str):
    session = await get_engine().stop(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Capture session not found")
    return session


@router.get("/capture/{session_id}")
async def get_capture(session_id: str):
    session = get_engine().get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Capture session not found")
    return session


@router.get("/capture")
async def list_captures():
    return get_engine().list_sessions()


@router.get("/capture/{session_id}/download")
async def download_capture(session_id: str):
    session = get_engine().get_session(session_id)
    if not session or not session.file_path:
        raise HTTPException(status_code=404, detail="Capture session or file not found")

    settings = get_settings()
    try:
        safe_path = validate_capture_path(session.file_path, settings.capture_dir)
    except ValidationError as exc:
        logger.warning("Path traversal blocked: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="Capture file not found on disk")

    return FileResponse(
        safe_path,
        media_type="application/octet-stream",
        filename=f"{session_id}.pcapng",
    )


@router.websocket("/ws/capture/{session_id}")
async def capture_websocket(websocket: WebSocket, session_id: str):
    """Stream decoded packets from a capture session via WebSocket."""
    await websocket.accept()
    engine = get_engine()
    try:
        async for pkt in engine.stream_packets(session_id):
            await websocket.send_json(pkt.model_dump())
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Capture WebSocket error")
        await websocket.send_json({"error": str(exc)})
    finally:
        await websocket.close()



