import json
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User, UserPreferences
from app.core.security import create_access_token, create_refresh_token

settings = get_settings()
router = APIRouter(prefix="/oauth", tags=["oauth"])
oauth = OAuth()

oauth.register(
    name='google',
    client_id=getattr(settings, "OAUTH_GOOGLE_CLIENT_ID", "mock_client_id"),
    client_secret=getattr(settings, "OAUTH_GOOGLE_CLIENT_SECRET", "mock_client_secret"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for('google_auth')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))

@router.get("/google/auth")
async def google_auth(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error))
    
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No userinfo in token")
    
    email = user_info.get("email")
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No email in userinfo")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Create a new user for oauth
        user = User(
            email=email,
            full_name=user_info.get("name"),
            hashed_password=None,
            oauth_provider="google",
            oauth_id=user_info.get("sub"),
        )
        db.add(user)
        await db.flush()
        db.add(UserPreferences(user_id=user.id))
        await db.commit()
        await db.refresh(user)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    return RedirectResponse(
        url=f"{frontend_url}/oauth/callback?access_token={access_token}&refresh_token={refresh_token}"
    )
