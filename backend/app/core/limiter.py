from slowapi import Limiter
from starlette.requests import Request
import jwt

def get_user_id_or_ip(request: Request) -> str:
    """Extracts User ID from JWT for per-user rate limits, falling back to 
    X-Forwarded-For/IP to properly handle users behind proxies and NATs."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        try:
            # We don't verify signature here; the actual route auth Depends() handles that securely.
            # This is purely to derive a bucket key for the rate limiter.
            payload = jwt.decode(token, options={"verify_signature": False})
            if sub := payload.get("sub"):
                return f"user:{sub}"
        except Exception:
            pass

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    
    return f"ip:{request.client.host if request.client else '127.0.0.1'}"

limiter = Limiter(key_func=get_user_id_or_ip, default_limits=["100/minute"])
