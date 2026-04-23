#!/usr/bin/env python3
"""
Script to check actual database schema for leave tables
"""
import sys
from sqlalchemy import inspect, text
from app.core.database import engine

def check_schema():
    """Check the actual schema of leave tables"""
    
    with engine.connect() as connection:
        inspector = inspect(engine)
        
        tables_to_check = ['leave_types', 'leave_allocations', 'leave_requests', 'leave_transactions']
        
        for table_name in tables_to_check:
            if table_name in inspector.get_table_names():
                print(f"\n{'='*60}")
                print(f"Table: {table_name}")
                print(f"{'='*60}")
                
                columns = inspector.get_columns(table_name)
                for col in columns:
                    col_name = col['name']
                    col_type = col['type']
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    print(f"  {col_name:30} {str(col_type):30} {nullable}")
            else:
                print(f"\n❌ Table {table_name} does NOT exist")

if __name__ == "__main__":
    try:
        check_schema()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
