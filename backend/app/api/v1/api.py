from fastapi import APIRouter, Depends
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints import inspections, rules, demo, health, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix='/auth', tags=['Authentication'])

api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(rules.router, prefix="/rules", tags=["Compliance Rules"], dependencies=[Depends(get_current_user)])
api_router.include_router(demo.router, prefix="/demo", tags=["Demo Suite"], dependencies=[Depends(get_current_user)])
api_router.include_router(health.router, prefix="/health", tags=["System Health"])
