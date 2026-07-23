"""
Pairing-based authentication for the AuraSense hub (roadmap stage F2).

A client pairs by presenting the hub's out-of-band pairing code to ``/api/v1/pair``
and receives a short-lived, HS256-signed JWT. Every ``/api/v1`` data route then
requires that token as an ``Authorization: Bearer`` credential.

Design note: tokens are stateless JWTs (no server-side session table). That keeps
the local hub simple and matches the "decode JWT local pairing secrets" intent,
at the cost of no per-token revocation before expiry — acceptable for a short TTL
on a LAN-local hub. A revocation/denylist table can be added later (D-phase) if
individual client revocation is needed.
"""
import os
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

logger = logging.getLogger("security")

# --- Configuration (from env; never commit real secrets) ---------------------
_DEV_SECRET = "dev-insecure-secret-change-me"
JWT_SECRET = os.getenv("AURASENSE_JWT_SECRET", _DEV_SECRET)
JWT_ALG = "HS256"
JWT_ISSUER = "aurasense-hub"
TOKEN_TTL_HOURS = int(os.getenv("AURASENSE_TOKEN_TTL_HOURS", "24"))
PAIRING_CODE = os.getenv("AURASENSE_PAIRING_CODE", "aurasense-dev")

if JWT_SECRET == _DEV_SECRET:
    logger.warning(
        "AURASENSE_JWT_SECRET is not set; using an insecure development secret. "
        "Set a strong AURASENSE_JWT_SECRET before any non-local deployment."
    )

# auto_error=False so a missing header yields our own 401 (with WWW-Authenticate)
# rather than FastAPI's default 403.
_bearer = HTTPBearer(auto_error=False)


def issue_token(client_id: str) -> tuple[str, int]:
    """Return ``(signed_jwt, expires_at_unix_seconds)`` for a paired client."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=TOKEN_TTL_HOURS)
    claims = {
        "sub": client_id,
        "iss": JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALG)
    return token, int(exp.timestamp())


def verify_pairing_code(code: str) -> bool:
    """Constant-time comparison against the configured pairing code."""
    return hmac.compare_digest(code or "", PAIRING_CODE)


def decode_token(token: str) -> dict:
    """Decode and validate a token, raising 401 on any failure (bad sig/exp/iss)."""
    try:
        return jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALG], issuer=JWT_ISSUER
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """FastAPI dependency: enforce a valid bearer token, returning its claims."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)
