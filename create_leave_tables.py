#!/usr/bin/env python3
"""
Script to create and update all leave management tables
"""
import sys
import logging
from sqlalchemy import inspect, text
from app.core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_or_update_leave_tables():
    """Create or update all leave management tables"""
    
    with engine.connect() as connection:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        logger.info(f"Existing tables: {existing_tables}")
        
        # Create leave_allocations if it doesn't exist
        if 'leave_allocations' not in existing_tables:
            try:
                sql = """
                CREATE TABLE leave_allocations (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    employee_id INT NOT NULL,
                    leave_type_id INT NOT NULL,
                    year INT NOT NULL,
                    allocated_days FLOAT DEFAULT 0,
                    used_days FLOAT DEFAULT 0,
                    carried_forward FLOAT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (leave_type_id) REFERENCES leave_types(id),
                    UNIQUE KEY uq_leave_allocation (employee_id, leave_type_id, year),
                    INDEX idx_employee_id (employee_id),
                    INDEX idx_year (year)
                )
                """
                logger.info("Creating leave_allocations table...")
                connection.execute(text(sql))
                connection.commit()
                logger.info("✓ Created leave_allocations table")
            except Exception as e:
                logger.error(f"✗ Failed to create leave_allocations: {e}")
        else:
            logger.info("✓ leave_allocations table already exists")
        
        # Create leave_requests if it doesn't exist
        if 'leave_requests' not in existing_tables:
            try:
                sql = """
                CREATE TABLE leave_requests (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    employee_id INT NOT NULL,
                    leave_type_id INT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    days FLOAT NOT NULL,
                    reason VARCHAR(500),
                    status VARCHAR(50) DEFAULT 'pending',
                    action_by INT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (leave_type_id) REFERENCES leave_types(id),
                    FOREIGN KEY (action_by) REFERENCES employees(id),
                    INDEX idx_employee_id (employee_id),
                    INDEX idx_status (status)
                )
                """
                logger.info("Creating leave_requests table...")
                connection.execute(text(sql))
                connection.commit()
                logger.info("✓ Created leave_requests table")
            except Exception as e:
                logger.error(f"✗ Failed to create leave_requests: {e}")
        else:
            logger.info("✓ leave_requests table already exists")
        
        # Create leave_transactions if it doesn't exist
        if 'leave_transactions' not in existing_tables:
            try:
                sql = """
                CREATE TABLE leave_transactions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    employee_id INT NOT NULL,
                    leave_type_id INT NOT NULL,
                    leave_request_id INT,
                    days FLOAT NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id),
                    FOREIGN KEY (leave_type_id) REFERENCES leave_types(id),
                    FOREIGN KEY (leave_request_id) REFERENCES leave_requests(id),
                    INDEX idx_employee_id (employee_id)
                )
                """
                logger.info("Creating leave_transactions table...")
                connection.execute(text(sql))
                connection.commit()
                logger.info("✓ Created leave_transactions table")
            except Exception as e:
                logger.error(f"✗ Failed to create leave_transactions: {e}")
        else:
            logger.info("✓ leave_transactions table already exists")
        
        logger.info("\nAll leave management tables are ready!")
        return True

if __name__ == "__main__":
    try:
        success = create_or_update_leave_tables()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
