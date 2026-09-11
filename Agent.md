# FURBEBE Engineering Rules

## Architecture

Frontend → FastAPI → PostgreSQL

Frontend에서 Supabase/PostgreSQL 직접 접근 금지.

## Frontend

React
React Router Framework
Vite
JavaScript
Tailwind

## Backend

Python 3.12+
FastAPI
SQLAlchemy
Alembic
PostgreSQL

## Commands

Frontend:
npm test
npm run lint
npm run build

Backend:
ruff check .
pytest

## Restrictions

- MySQL 금지
- Redux 금지
- Redis 1차 도입 금지
- AI 1차 도입 금지
- migration 삭제 금지
- production data 삭제 금지