"""FastAPI app factory. The repository is injected at startup (ADR-012). No routes until the learning gate clears."""

from __future__ import annotations

from fastapi import FastAPI

from pios.repositories import Repository


def create_app(repository: Repository) -> FastAPI:
    app = FastAPI(title="PIOS")
    app.state.repository = repository
    return app


__all__ = ["create_app"]
