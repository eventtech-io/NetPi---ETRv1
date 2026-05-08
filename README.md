!!!!UNTESTED!!!

# NetPi 26

**Modern network analyzer and DMX512/RDM test tool for Raspberry Pi 4 and Pi 5.**

## Quick Start

```bash
sudo bash deploy/install.sh
```

Then open `http://<pi-ip>:8080`.

## Security

Set `NETPI_API_KEY` to enable API key authentication:

```ini
# /etc/systemd/system/netpi.service [Service] section
Environment=NETPI_API_KEY=your-secret-key
Environment=NETPI_CORS_ORIGINS=http://192.168.1.100
```

Then add `X-API-Key: your-secret-key` to all requests.

## Bug Fixes (v0.2.1)

- `ws_router` ImportError that prevented startup
- `async for` on `asyncio.as_completed()` (TypeError)
- `datetime` fields assigned `float` (Pydantic ValidationError)
- `tty.tcsendbreak` / `termios.BOTHER` — replaced UART backend with PySerial
- DIP switch overflow for address 512
- `ethtool --cable-test` called in `is_available()` (took link down)
- Blocking serial I/O on event loop thread
- CDP address TLV field offset errors
- `CDPPacket` mutable default fields
- `{"error": "..."}` HTTP 200 replaced with proper `HTTPException`
- Inline `__import__()` calls removed
- Single TX task shared across all universes
- `dialout` group not added in installer
