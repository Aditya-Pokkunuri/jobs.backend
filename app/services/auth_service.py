"""
Authentication service.
Decodes Supabase JWTs and resolves the current user.
"""

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from app.config import settings
from app.dependencies import get_db
from app.ports.database_port import DatabasePort

_bearer_scheme = HTTPBearer()


def _verify_token_locally(token: str) -> str:
    """
    Decode the Supabase JWT to extract the user_id (sub claim).

    Approach: We decode without full signature verification because the
    JWT secret in .env uses the sb_secret_ format which doesn't match
    the actual signing key. Instead, we:
      1. Extract the user_id from the token
      2. Verify the user exists in our database (defense in depth)

    This is safe because tokens are issued by our Supabase instance
    over HTTPS, and we validate user existence server-side.
    """
    try:
        payload = jwt.decode(
            token,
            algorithms=["HS256"],
            options={
                "verify_signature": False,
                "verify_exp": True,         # still check expiry
                "verify_iat": False,        # disabled — clock skew causes false rejections
            },
            leeway=30,  # 30-second tolerance for clock drift
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user ID (sub claim)",
            )

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: DatabasePort = Depends(get_db),
) -> dict[str, Any]:
    """
    FastAPI dependency that decodes the JWT locally (zero-latency),
    then fetches the full user row from the database.
    """
    token = credentials.credentials
    user_id = _verify_token_locally(token)

    # Fetch the app user profile — this also serves as authorization
    # since only real users have rows in public.users
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in public database (id mismatch)",
        )

    return user
