#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Enable pg_trgm extension for fuzzy search
python -c "
from sqlmodel import Session, text
from app.core.db import engine
with Session(engine) as s:
    s.exec(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
    s.commit()
"

# Run migrations
alembic upgrade head

# Create initial data in DB
python app/initial_data.py

# Seed product data from CSV (idempotent – skips if items exist)
python app/seed_data.py
