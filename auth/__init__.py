from fastapi import APIRouter
from .views import router as auth_router

router = APIRouter(prefix="/auth", tags=["AUTH ENDPOINTS"])


router.include_router(auth_router)
