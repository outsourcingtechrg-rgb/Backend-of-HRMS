#!/usr/bin/env python3
"""
Direct script to add missing columns to leave_types table
"""
import sys
import logging
from sqlalchemy import inspect, text
from app.core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_columns():
    """Add missing columns to leave_types table"""
    
    with engine.connect() as connection:
        inspector = inspect(engine)
        
        # Check if leave_types table exists
        if 'leave_types' not in inspector.get_table_names():
            logger.error("leave_types table does not exist!")
            return False
        
        existing_columns = {
            col["name"] for col in inspector.get_columns("leave_types")
        }
        
        logger.info(f"Existing columns in leave_types: {existing_columns}")
        
        # Define columns to add
        columns_to_add = {
            'code': "VARCHAR(255) UNIQUE",
            'max_carry_forward': "FLOAT",
            'allow_negative_balance': "BOOLEAN DEFAULT 0",
            'gender_specific': "VARCHAR(255)",
            'reset_month': "INT",
            'min_days': "FLOAT",
            'max_days_per_request': "FLOAT",
            'extradata': "JSON",
        }
        
        # Add missing columns
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE leave_types ADD COLUMN {col_name} {col_type}"
                    logger.info(f"Executing: {sql}")
                    connection.execute(text(sql))
                    connection.commit()
                    logger.info(f"✓ Added column: {col_name}")
                except Exception as e:
                    logger.error(f"✗ Failed to add {col_name}: {e}")
            else:
                logger.info(f"✓ Column {col_name} already exists")
        
        logger.info("All columns processed successfully!")
        return True

if __name__ == "__main__":
    try:
        success = add_missing_columns()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
