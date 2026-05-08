"""Input validation for capture and BPF filters."""
from pathlib import Path

from netpi_core.config import get_settings


class ValidationError(ValueError):
    """Raised when user input fails security validation."""


def sanitize_bpf(expression: str | None) -> str | None:
    """Validate a BPF expression against an allowed character set.

    Raises ValidationError if potentially dangerous characters are found.
    """
    if expression is None:
        return None
    if expression == "":
        return ""

    settings = get_settings()
    allowed = set(settings.bpf_allowed_chars)

    for char in expression:
        if char not in allowed:
            raise ValidationError(
                f"Disallowed character {char!r} in BPF expression. "
                f"Allowed: {settings.bpf_allowed_chars!r}"
            )

    # Extra guard: reject common shell injection patterns
    dangerous_patterns = (";", "`", "${", "|", "&&", ">>", "<")
    for pat in dangerous_patterns:
        if pat in expression:
            raise ValidationError(
                f"BPF expression contains forbidden sequence {pat!r}"
            )

    return expression


def validate_capture_path(file_path: str, data_dir: str) -> Path:
    """Ensure a capture file path is within the designated data directory.

    Raises ValidationError on path traversal attempts.
    """
    try:
        base = Path(data_dir).resolve()
        target = Path(file_path).resolve()
    except Exception as exc:
        raise ValidationError(f"Invalid path: {exc}")

    # Ensure the resolved path is actually under base
    try:
        target.relative_to(base)
    except ValueError:
        raise ValidationError(
            f"Path traversal detected: {file_path} is outside {data_dir}"
        )

    return target



