from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import CRUDBase
from app.models.models import AssessmentSession
from app.models.enums import SessionStatus


class CRUDAssessmentSession(CRUDBase[AssessmentSession]):
    async def get_by_token_hash(
        self, db: AsyncSession, *, token_hash: str
    ) -> Optional[AssessmentSession]:
        result = await db.execute(
            select(self.model).filter(self.model.token_hash == token_hash)
        )
        return result.scalars().first()

    async def get_active_session_by_patient(
        self, db: AsyncSession, *, patient_id: UUID
    ) -> Optional[AssessmentSession]:
        stmt = select(self.model).filter(
            and_(
                self.model.patient_id == patient_id,
                or_(
                    self.model.status == SessionStatus.INITIALIZED,
                    self.model.status == SessionStatus.STARTED,
                ),
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_active_session_by_token_hash(
        self, db: AsyncSession, *, token_hash: str
    ) -> Optional[AssessmentSession]:
        """Find an active (not completed/abandoned) session by its token hash."""
        stmt = select(self.model).filter(
            and_(
                self.model.token_hash == token_hash,
                or_(
                    self.model.status == SessionStatus.INITIALIZED,
                    self.model.status == SessionStatus.STARTED,
                ),
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_with_steps(
        self, db: AsyncSession, *, session_id: UUID
    ) -> Optional[AssessmentSession]:
        stmt = (
            select(self.model)
            .filter(self.model.id == session_id)
            .options(selectinload(self.model.steps))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_with_steps_and_attempts(
        self, db: AsyncSession, *, session_id: UUID
    ) -> Optional[AssessmentSession]:
        stmt = (
            select(self.model)
            .filter(self.model.id == session_id)
            .options(
                selectinload(self.model.steps),
                selectinload(self.model.attempts),
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()


session_repo = CRUDAssessmentSession(AssessmentSession)
