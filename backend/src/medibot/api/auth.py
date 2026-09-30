"""Login + JWT (R1.4, R6, D6, D25).

The role lives only in the signed token. `/chat` reads it through `current_user`, so a client
can't claim another role: changing the token's payload breaks its signature.
"""

import logging
import os
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

log = logging.getLogger(__name__)

# Demo accounts from the brief (REQUIREMENTS section 2): username -> (role, bcrypt hash).
# The passwords are public in the brief; only hashes are stored so the check is a real one.
USERS: dict[str, tuple[str, str]] = {
    "dr.mehta": ("doctor", "$2b$10$BbPMkEZqlyTtIxJ5K42hUuvSV17oeAr8D/D8j8CCOxw/7aJ5DADhi"),
    "nurse.priya": ("nurse", "$2b$10$Y792ou/dAtBvAx//d/o84.TpG9V5rr0h/lQ3Df2dI2eFldY3NXTiq"),
    "billing.ravi": (
        "billing_executive",
        "$2b$10$egywIlfpzCYKAhJ90MpPlOhCtvApy5.NxYc5bGVe1TUUQRQRBK/Mi",
    ),
    "tech.anand": ("technician", "$2b$10$wSo49sdjeC86ybi9Hc2p.e/7TE0GhiDDPre7gCtYRelZ/z3yh0RLm"),
    "admin.sys": ("admin", "$2b$10$xCO5YrefpQ6xcHO6B/NNWu73XQgVlB96k492jeeqO/qo2HDICOV.2"),
}

ALGORITHM = "HS256"
TOKEN_TTL = timedelta(hours=8)
_SECRET = os.environ.get("MEDIBOT_JWT_SECRET") or ""
if not _SECRET:
    _SECRET = secrets.token_urlsafe(32)
    log.warning("MEDIBOT_JWT_SECRET not set: using a random per-process secret (dev only)")

# Compared against when the username is unknown, so both paths cost one bcrypt check.
_DUMMY_HASH = bcrypt.hashpw(b"x", bcrypt.gensalt(rounds=10))


class User(BaseModel):
    username: str
    role: str


def authenticate(username: str, password: str) -> User | None:
    role, hashed = USERS.get(username, (None, _DUMMY_HASH.decode()))
    ok = bcrypt.checkpw(password.encode(), hashed.encode())
    return User(username=username, role=role) if ok and role else None


def create_token(user: User) -> str:
    now = datetime.now(UTC)
    payload = {"sub": user.username, "role": user.role, "iat": now, "exp": now + TOKEN_TTL}
    return jwt.encode(payload, _SECRET, algorithm=ALGORITHM)


_bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> User:  # noqa: B008
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "invalid or missing token", {"WWW-Authenticate": "Bearer"}
    )
    if creds is None:
        raise unauthorized
    try:
        payload = jwt.decode(creds.credentials, _SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError as e:
        raise unauthorized from e
    username, role = payload.get("sub"), payload.get("role")
    # the token must still match a known account and its current role
    if username not in USERS or USERS[username][0] != role:
        raise unauthorized
    return User(username=username, role=role)
