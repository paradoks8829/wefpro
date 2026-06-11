import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()

DEFAULT_WINDOW_SECONDS = 60
DEFAULT_MAX_ATTEMPTS = 5


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(
    request: Request,
    scope: str,
    *,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> None:
    key = f"{scope}:{_client_ip(request)}"
    now = time.time()

    with _lock:
        recent = [ts for ts in _attempts[key] if now - ts < window_seconds]
        if len(recent) >= max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много попыток. Подождите минуту и попробуйте снова.",
            )
        recent.append(now)
        _attempts[key] = recent
