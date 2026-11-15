from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user
from app.schemas.schemas import ReportCreate, ReportOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(body: ReportCreate, current_user=Depends(get_current_user)):
    raise NotImplementedError


@router.get("/mine")
async def my_reports(current_user=Depends(get_current_user)):
    raise NotImplementedError