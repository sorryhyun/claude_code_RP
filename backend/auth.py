"""
Authentication middleware and utilities for JWT token-based authentication.

SECURITY NOTES:
- Passwords are hashed using bcrypt before comparison
- JWT tokens are issued upon successful login
- Tokens are sent via X-API-Key header for all endpoints
- Always use HTTPS in production to protect credentials in transit
- Rate limiting via slowapi to prevent brute force attacks
"""

import logging
import os
import secrets
import sys
from datetime import datetime, timedelta

import bcrypt
import jwt
from core import get_settings
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("Auth")


def get_api_key_hash_from_env() -> str:
    """
    Get the hashed API key from environment variable.

    The API_KEY_HASH should be a bcrypt hash generated from your password.
    Use the generate_hash.py script to create one.

    Raises:
        SystemExit: If API_KEY_HASH is not set in production
    """
    # Prefer direct environment variable (supports runtime overrides in tests)
    api_key_hash = os.getenv("API_KEY_HASH") or get_settings().api_key_hash
    if api_key_hash:
        return api_key_hash

    # API_KEY_HASH is required
    logger.error("❌ ERROR: API_KEY_HASH is not set in environment variables!")
    logger.error("❌ Authentication cannot work without a password configured.")
    logger.error("💡 To fix: Run 'python generate_hash.py' to create a hash, then add it to .env")
    sys.exit(1)


def get_guest_password_hash_from_env() -> str | None:
    """
    Get the hashed guest password from environment variable.

    The GUEST_PASSWORD_HASH should be a bcrypt hash generated from your guest password.
    Use the generate_hash.py script to create one.

    Returns:
        str | None: The guest password hash if set, None otherwise
    """
    return os.getenv("GUEST_PASSWORD_HASH") or get_settings().guest_password_hash


def is_guest_login_enabled() -> bool:
    """
    Check if guest login is enabled via environment variable.

    Returns:
        bool: True if guest login is enabled, False otherwise
    """
    env_value = os.getenv("ENABLE_GUEST_LOGIN")
    if env_value is not None:
        return str(env_value).lower() in {"1", "true", "yes", "on"}
    return get_settings().enable_guest_login


def validate_api_key(provided_key: str) -> bool:
    """
    Validate the provided API key against the configured hashed password.

    Uses constant-time comparison via bcrypt to prevent timing attacks.

    Args:
        provided_key: The plaintext password/API key provided by the user

    Returns:
        bool: True if the password matches, False otherwise
    """
    try:
        expected_hash = get_api_key_hash_from_env()
        # bcrypt.checkpw handles constant-time comparison internally
        return bcrypt.checkpw(provided_key.encode("utf-8"), expected_hash.encode("utf-8"))
    except Exception as e:
        logger.error(f"❌ Error validating API key: {e}")
        return False


def validate_password_with_role(provided_key: str) -> str | None:
    """
    Validate the provided password and return the user's role.

    Checks against both admin and guest password hashes (if guest login is enabled).

    Args:
        provided_key: The plaintext password provided by the user

    Returns:
        str | None: 'admin' if admin password matches, 'guest' if guest password matches,
                    None if no password matches
    """
    try:
        # Check admin password
        admin_hash = get_api_key_hash_from_env()
        if bcrypt.checkpw(provided_key.encode("utf-8"), admin_hash.encode("utf-8")):
            return "admin"

        # Check guest password if configured and enabled
        if is_guest_login_enabled():
            guest_hash = get_guest_password_hash_from_env()
            if guest_hash:
                if bcrypt.checkpw(provided_key.encode("utf-8"), guest_hash.encode("utf-8")):
                    return "guest"

        return None
    except Exception as e:
        logger.error(f"❌ Error validating password: {e}")
        return None


def get_jwt_secret() -> str:
    """
    Get the JWT secret key from environment variable.

    If not set, generates a random secret for the session.
    WARNING: Using a random secret means tokens won't survive server restarts.

    Returns:
        str: The JWT secret key
    """
    jwt_secret = os.getenv("JWT_SECRET") or get_settings().jwt_secret
    if not jwt_secret:
        # Generate a random secret for this session
        jwt_secret = secrets.token_hex(32)
        logger.warning("⚠️  WARNING: JWT_SECRET not set. Using random session secret.")
        logger.warning("⚠️  Tokens will be invalidated on server restart.")
        logger.warning("💡 To fix: Set JWT_SECRET in .env to a secure random string")
    return jwt_secret


def generate_jwt_token(role: str = "admin", expiration_hours: int = 168, user_id: str | None = None) -> str:
    """
    Generate a JWT token for authentication.

    Args:
        role: User role ('admin' or 'guest')
        expiration_hours: Hours until token expires (default: 168 = 7 days)
        user_id: Unique identifier for the authenticated user (auto-generated for guests)

    Returns:
        str: Encoded JWT token
    """
    # Default user_id handling (ensures each guest gets a unique identity)
    if user_id is None:
        if role == "guest":
            user_id = f"guest-{secrets.token_hex(6)}"
        else:
            user_id = "admin"

    secret = get_jwt_secret()
    payload = {
        "exp": datetime.utcnow() + timedelta(hours=expiration_hours),
        "iat": datetime.utcnow(),
        "type": "access_token",
        "role": role,
        "user_id": user_id,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def validate_jwt_token(token: str) -> dict | None:
    """
    Validate a JWT token and return its payload.

    Args:
        token: The JWT token to validate

    Returns:
        dict | None: Token payload if valid, None otherwise
    """
    try:
        secret = get_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("⚠️  JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"⚠️  Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error validating JWT token: {e}")
        return None


def get_role_from_token(token: str) -> str | None:
    """
    Extract the role from a JWT token.

    Args:
        token: The JWT token

    Returns:
        str | None: The role ('admin' or 'guest') if valid, None otherwise
    """
    payload = validate_jwt_token(token)
    if payload:
        return payload.get("role", "admin")  # Default to admin for old tokens
    return None


def get_user_id_from_token(token: str) -> str | None:
    """
    Extract the user_id from a JWT token.

    Falls back to role when missing for backward compatibility with legacy tokens.
    """
    payload = validate_jwt_token(token)
    if not payload:
        return None

    # Legacy tokens didn't include user_id; fallback to role-based defaults
    if "user_id" not in payload:
        role = payload.get("role", "admin")
        return "admin" if role == "admin" else "guest"

    return payload.get("user_id")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check JWT token authentication.

    Authentication methods:
    - REST API: X-API-Key header (contains JWT token)

    Excluded paths (no auth required):
    - /auth/login - Login endpoint
    - /health - Health check
    - /docs, /openapi.json, /redoc - API documentation
    """

    # Paths that don't require authentication
    EXCLUDED_PATHS = [
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/auth/login",
        "/health",
    ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for excluded paths
        if path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Skip auth for static assets (bundled frontend)
        if path.startswith("/assets/") or path.endswith((".js", ".css", ".svg", ".png", ".ico", ".woff", ".woff2")):
            return await call_next(request)

        # Skip auth for profile picture requests (needed for <img> tags)
        if path.startswith("/agents/") and path.endswith("/profile-pic"):
            return await call_next(request)

        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract token from header
        token = request.headers.get("X-API-Key")

        # Validate JWT token
        token_payload = validate_jwt_token(token) if token else None
        if not token_payload:
            # Get origin from request headers for CORS
            origin = request.headers.get("origin")
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Invalid or missing authentication token"}
            )
            # Add CORS headers to error response
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"
            return response

        # Store the role and user_id in request state for later use
        request.state.user_role = token_payload.get("role", "admin")
        request.state.user_id = token_payload.get("user_id") or (
            "admin" if request.state.user_role == "admin" else "guest"
        )

        # Continue processing the request
        response = await call_next(request)
        return response


def require_admin(request: Request):
    """
    Dependency function to require admin role for an endpoint.

    Args:
        request: The FastAPI request object

    Raises:
        HTTPException: 403 Forbidden if user is not an admin

    Usage:
        @app.delete("/rooms/{room_id}", dependencies=[Depends(require_admin)])
        async def delete_room(room_id: int):
            ...
    """
    user_role = getattr(request.state, "user_role", None)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires admin privileges. Guests can chat but cannot modify rooms, agents, or messages.",
        )
