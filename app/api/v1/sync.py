# """
# Sync management API endpoints
# """
# from fastapi import APIRouter, HTTPException, status
# from app.background import get_sync_status, trigger_manual_sync

# router = APIRouter()


# @router.get("/status")
# async def get_sync_status_endpoint():
#     """Get the current ZKT sync status"""
#     return get_sync_status()


# @router.post("/trigger")
# async def trigger_sync():
#     """Manually trigger a sync cycle"""
#     result = await trigger_manual_sync()
    
#     if not result.get("success"):
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=result.get("message", "Sync failed")
#         )
    
#     return result


# from fastapi import APIRouter
# from app.background.scheduler import get_scheduler_status
# from app.background.Background_jobs import my_scheduled_function

# router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


# # Check background worker
# @router.get("/status")
# def scheduler_status():
#     return {
#         "scheduler": get_scheduler_status()
#     }


# # Manually trigger task
# @router.post("/run")
# def run_job():
#     result = my_scheduled_function()
#     return {
#         "message": "Job executed manually",
#         "result": result
#     }