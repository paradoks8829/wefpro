import secrets
import time
from threading import Lock

_used_nonces: dict[str, float] = {}
_lock = Lock()
NONCE_TTL_SECONDS = 3600


def generate_form_nonce() -> str:
    return secrets.token_urlsafe(24)


def consume_form_nonce(nonce: str) -> bool:
    if not nonce:
        return False

    now = time.time()
    with _lock:
        expired = [key for key, ts in _used_nonces.items() if now - ts > NONCE_TTL_SECONDS]
        for key in expired:
            del _used_nonces[key]

        if nonce in _used_nonces:
            return False

        _used_nonces[nonce] = now
        return True
