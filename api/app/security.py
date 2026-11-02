"""Password hashing, signed session tokens and sign-in lockout."""

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time

SCRYPT = {"n": 2**14, "r": 8, "p": 1}
MAX_FAILED = 5
LOCK_SECONDS = 10 * 60


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **SCRYPT)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password, stored):
    try:
        scheme, salt_b64, digest_b64 = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), dklen=32, **SCRYPT)
    return hmac.compare_digest(digest, base64.b64decode(digest_b64))


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(user_id, session_version, secret, hours, now=None):
    payload = {"uid": user_id, "ver": session_version, "exp": int((now or time.time()) + hours * 3600)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_token(token, secret, now=None):
    """The token's payload, or None if it is forged, malformed or expired."""
    try:
        body, sig = token.split(".")
        expected = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_unb64(body))
    except (ValueError, TypeError):
        return None
    if payload.get("exp", 0) < (now or time.time()):
        return None
    return payload


class LoginLimiter:
    """Locks an email for 10 minutes after 5 failed sign-ins (in memory)."""

    def __init__(self):
        self._failures = {}
        self._lock = threading.Lock()

    def locked_for(self, email, now=None):
        now = now or time.time()
        with self._lock:
            count, until = self._failures.get(email, (0, 0))
            return max(0, int(until - now)) if count >= MAX_FAILED else 0

    def failed(self, email, now=None):
        now = now or time.time()
        with self._lock:
            count, until = self._failures.get(email, (0, 0))
            if count >= MAX_FAILED and until <= now:
                count = 0
            count += 1
            self._failures[email] = (count, now + LOCK_SECONDS if count >= MAX_FAILED else 0)

    def succeeded(self, email):
        with self._lock:
            self._failures.pop(email, None)


limiter = LoginLimiter()
