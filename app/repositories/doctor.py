from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import CRUDBase
from app.models.models import Doctor


class CRUDDoctor(CRUDBase[Doctor]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[Doctor]:
        # Case-insensitive lookup (normalise to lowercase)
        normalized_email = email.strip().lower()
        result = await db.execute(
            select(self.model).filter(func.lower(self.model.email) == normalized_email)
        )
        return result.scalars().first()


doctor_repo = CRUDDoctor(Doctor)
