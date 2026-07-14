from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dispositions import router as dispositions_router
from app.api.v1.rewards import router as rewards_router
from app.api.v1.sales import router as sales_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(dispositions_router)
api_router.include_router(rewards_router)
api_router.include_router(sales_router)
api_router.include_router(admin_router)
