from jose import JWTError, jwt

from app.core.config import settings


def decode_access_token(token: str) -> dict:
    if not settings.JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not configured")

    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )

    if payload.get("type") != "access":
        raise JWTError("Invalid token type")

    return payload
