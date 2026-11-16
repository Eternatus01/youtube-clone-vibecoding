from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.schemas.schemas import ReportCreate, ReportOut
from app.services import reports as reports_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(
    body: ReportCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await reports_service.create_report(db, body, current_user)


@router.get("/mine", response_model=list[ReportOut])
async def my_reports(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await reports_service.list_mine(db, current_user)