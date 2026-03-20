from sqlalchemy import text, create_engine
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS employee_id INT UNIQUE NULL"))
    conn.commit()
    print("✓ employee_id column added to employees table!")
