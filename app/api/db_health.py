from fastapi import APIRouter
from app.core.database import test_db_connection

router = APIRouter(tags=["Database"])

@router.get("/db-health")
def db_health_check():
    try:
        test_db_connection()
        return {
            "database": "connected",
            "status": "ok"
        }
    except Exception as e:
        return {
            "database": "error",
            "status": "failed",
            "detail": str(e)
        }
