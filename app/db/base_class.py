from typing import Any
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""
    id: Any
    __name__: str

    # Generate __tablename__ automatically if not specified
    # but since we want strict mappings we'll define tablename on each model class.
    pass
