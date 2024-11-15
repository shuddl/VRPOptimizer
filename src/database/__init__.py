# src/database/__init__.py
"""Database module initialization."""

from src.database.database import DatabaseConnection, DatabaseError

__all__ = ["DatabaseConnection", "DatabaseError"]
