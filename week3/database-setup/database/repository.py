from typing import Generic, TypeVar, Type, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

"""
Generic Repository Module

This module provides a generic repository for database operations.
It supports basic CRUD operations and additional methods for querying and updating data.
"""

T = TypeVar("T")


class GenericRepository(Generic[T]):
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def create(self, obj: T) -> T:
        self.session.add(obj)
        self.session.commit()
        return obj

    def get(
        self,
        id: str,
    ) -> Optional[T]:
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_all(
        self,
    ) -> List[T]:
        return self.session.query(self.model).all()

    def update(
        self,
        obj: T,
    ) -> T:
        self.session.merge(obj)
        self.session.commit()
        return obj

    def delete(
        self,
        id: str,
    ) -> None:
        obj = self.get(id)
        if obj:
            self.session.delete(obj)
            self.session.commit()

    def get_latest(
        self,
        n: int = 1,
    ) -> List[T]:
        return (
            self.session.query(self.model).order_by(desc(self.model.id)).limit(n).all()
        )

    def count(
        self,
    ) -> int:
        return self.session.query(self.model).count()

    def exists(
        self,
        **kwargs,
    ) -> bool:
        return self.session.query(
            self.model.query.filter_by(**kwargs).exists()
        ).scalar()
