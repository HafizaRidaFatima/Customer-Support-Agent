from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import get_current_user
from backend.app.config import ADMIN_CODE
from backend.app.schemas.auth import AdminRegistration, Token, UserLogin, UserRegistration
from backend.app.services.auth_service import (
    authenticate_user,
    create_access_token,
    register_user,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _register(username: str, password: str, email: str, role: str) -> dict[str, str]:
    try:
        user = register_user(username, password, email, role)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return {"message": "Account created successfully.", **user}


@router.post("/register/user", status_code=status.HTTP_201_CREATED)
def register_customer(body: UserRegistration) -> dict[str, str]:
    return _register(body.username, body.password, str(body.email), "customer")


@router.post("/register/admin", status_code=status.HTTP_201_CREATED)
def register_admin(body: AdminRegistration) -> dict[str, str]:
    if not ADMIN_CODE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin registration is not configured.",
        )
    if body.admin_code != ADMIN_CODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin registration code.",
        )
    return _register(body.username, body.password, str(body.email), "admin")


@router.post("/log-in", response_model=Token)
def log_in(body: UserLogin) -> dict[str, str]:
    user = authenticate_user(body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
    }


@router.get("/me")
def get_authenticated_user(user: dict = Depends(get_current_user)) -> dict:
    return {"user": user}
