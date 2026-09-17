"""
Authentication router.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.schemas import Token, LoginRequest, TokenRefresh, UserCreate, UserResponse
from app.repositories.user_repository import UserRepository
from app.models import UserRole
from app.services.refresh_token_service import RefreshTokenService
from app.services.audit_service import AuditService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.

    - **email**: User email address
    - **password**: User password
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(credentials.email)

    if not user or not verify_password(credentials.password, user.hashed_password):
        # Log failed login attempt
        audit_service = AuditService(db)
        if user:
            await audit_service.log_authentication(
                user_id=user.id,
                action="login",
                success=False,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    # Create database-backed refresh token
    refresh_token_service = RefreshTokenService(db)
    refresh_token, _ = await refresh_token_service.create_token(user.id)
    
    # Log successful login
    audit_service = AuditService(db)
    await audit_service.log_authentication(
        user_id=user.id,
        action="login",
        success=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_refresh: TokenRefresh,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token with rotation.

    - **refresh_token**: Valid refresh token
    
    Returns new access token and new refresh token (rotation).
    Old refresh token is revoked.
    """
    # Verify and rotate the refresh token
    refresh_token_service = RefreshTokenService(db)
    result = await refresh_token_service.rotate_token(token_refresh.refresh_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    new_refresh_token, refresh_token_obj = result
    
    # Create new access token
    access_token = create_access_token(data={"sub": refresh_token_obj.user_id})
    
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    request: Request,
    token_refresh: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Logout by revoking the refresh token.

    - **refresh_token**: Refresh token to revoke
    """
    from app.core.security import decode_token
    
    # Decode the refresh token to get user_id
    payload = decode_token(token_refresh.refresh_token)
    user_id = payload.get("sub") if payload else None
    
    # Revoke the token
    refresh_token_service = RefreshTokenService(db)
    token_hash = refresh_token_service._hash_token(token_refresh.refresh_token)
    await refresh_token_service.revoke_token(token_hash)
    
    # Log logout
    if user_id:
        audit_service = AuditService(db)
        await audit_service.log_authentication(
            user_id=user_id,
            action="logout",
            success=True,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    
    await db.commit()
    
    return {"message": "Successfully logged out"}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user (admin only in production).

    - **email**: User email address
    - **password**: User password (min 8 characters)
    - **full_name**: User's full name
    - **role**: User role (admin, faculty, staff)
    """
    user_repo = UserRepository(db)

    # Check if user already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = await user_repo.create_user(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        department=user_data.department
    )

    await db.commit()

    return user
