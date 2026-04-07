from fastapi import APIRouter

from src.api.v0.shortener.endpoints import router as shortner_router
from src.api.v0.system.endpoints import router as system_router

v0_router = APIRouter(prefix="/v0")
v0_router.include_router(system_router)
v0_router.include_router(shortner_router)
