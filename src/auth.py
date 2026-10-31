from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import defaultdict, deque
from threading import Lock


SESSION_COOKIE = "esg_session"
CSRF_COOKIE = "esg_csrf"
SESSION_MAX_AGE = 60 * 60 * 8  # 8 hours

SESSION_SECRET = os.getenv("SESSION_SECRET", "")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempts_lock = Lock()
_revoked_sessions: set[str] = set()
_revoked_sessions_lock = Lock()


def _valid_password(password: str) -> bool:
    """Verify a PBKDF2 password hash stored in the environment.

    Expected format:
    pbkdf2_sha256$iterations$salt_hex$digest_hex
    """
    if not ADMIN_PASSWORD_HASH:
        return False

    try:
        algorithm, iterations_text, salt_hex, digest_hex = (
            ADMIN_PASSWORD_HASH.split("$", 3)
        )
        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)
        if not 100_000 <= iterations <= 2_000_000:
            return False

        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def login_allowed(client_ip: str) -> bool:
    now = time.monotonic()
    with _attempts_lock:
        attempts = _attempts[client_ip]
        while attempts and now - attempts[0] > 300:
            attempts.popleft()
        return len(attempts) < 5


def record_login_failure(client_ip: str) -> None:
    now = time.monotonic()
    with _attempts_lock:
        attempts = _attempts[client_ip]
        while attempts and now - attempts[0] > 300:
            attempts.popleft()
        attempts.append(now)


def clear_login_failures(client_ip: str) -> None:
    with _attempts_lock:
        _attempts.pop(client_ip, None)


def verify_admin_password(password: str) -> bool:
    return _valid_password(password)


def create_session() -> str:
    if not SESSION_SECRET:
        raise RuntimeError("SESSION_SECRET is not configured")

    payload = json.dumps(
        {"role": "admin", "iat": int(time.time())},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signed_data = b"esg-session-v1." + encoded_payload
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"), signed_data, hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return (
        f"{encoded_payload.decode('ascii')}."
        f"{encoded_signature.decode('ascii')}"
    )
def revoke_session(token: str | None) -> None:
    """Invalidate a session token until the server restarts."""
    if not token:
        return

    with _revoked_sessions_lock:
        _revoked_sessions.add(
            hashlib.sha256(token.encode("utf-8")).hexdigest()
        )

def validate_session(token: str | None) -> bool:
    if not token or not SESSION_SECRET:
        return False

    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        payload_bytes = encoded_payload.encode("ascii")
        signature_bytes = encoded_signature.encode("ascii")
        payload = base64.urlsafe_b64decode(
            payload_bytes + b"=" * (-len(payload_bytes) % 4)
        )
        signature = base64.urlsafe_b64decode(
            signature_bytes + b"=" * (-len(signature_bytes) % 4)
        )
        expected_signature = hmac.new(
            SESSION_SECRET.encode("utf-8"),
            b"esg-session-v1." + payload_bytes,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return False

        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with _revoked_sessions_lock:
            if token_hash in _revoked_sessions:
                return False

        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            return False
        issued_at = data.get("iat")
        now = int(time.time())
        return (
            data.get("role") == "admin"
            and isinstance(issued_at, int)
            and not isinstance(issued_at, bool)
            and issued_at <= now
            and now - issued_at <= SESSION_MAX_AGE
        )
    except (ValueError, TypeError, UnicodeError):
        return False


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def valid_csrf_token(cookie_token: str | None, header_token: str | None) -> bool:
    return bool(
        cookie_token
        and header_token
        and hmac.compare_digest(cookie_token, header_token)
    )
