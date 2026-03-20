from sqlalchemy import text, create_engine
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS gender VARCHAR(50) NOT NULL DEFAULT 'Not Specified'"))
    conn.commit()
    print("✓ Gender column added to employees table!")
