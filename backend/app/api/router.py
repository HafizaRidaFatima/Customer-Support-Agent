from fastapi import APIRouter

from backend.app.api.routes.approvals import router as approvals_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.complaints import router as complaints_router
from backend.app.api.routes.customers import router as customers_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.tickets import router as tickets_router


api_router = APIRouter(prefix="/api")

api_router.include_router(approvals_router)
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(complaints_router)
api_router.include_router(customers_router)
api_router.include_router(health_router)
api_router.include_router(tickets_router)
