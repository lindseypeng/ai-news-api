import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from database.database_utils import DatabaseUtils

"""
Session Module

This module provides a session for database operations.
"""

engine = create_engine(DatabaseUtils.get_connection_string())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def db_session() -> Generator:
    """Database Session Dependency.

    This function provides a database session for each request.
    It ensures that the session is committed after successful operations.
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as ex:
        session.rollback()
        logging.error(ex)
        raise ex
    finally:
        session.close()
