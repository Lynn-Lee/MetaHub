from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router)

# 后续按 DEV-TASKS 逐步接入：
#   T6.2  datasources / tables / columns / search
#   T5.1  annotations
#   V0.5  domains / tags / dicts / todos / changes
#   V1.0  security / subscriptions / dashboard / admin / semantic
