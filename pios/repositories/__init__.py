"""Persistence behind one abstract interface (ADR-012). The only place SQL may live."""

from pios.repositories.interface import Repository, StoredEvent
from pios.repositories.postgres import PostgresRepository
from pios.repositories.sqlite import SqliteRepository

__all__ = ["PostgresRepository", "Repository", "SqliteRepository", "StoredEvent"]
