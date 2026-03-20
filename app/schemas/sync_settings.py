from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SyncSettingsBase(BaseModel):
    """Base sync settings schema."""
    device_ip: str
    sync_interval_minutes: int
    is_enabled: bool


class SyncSettingsCreate(SyncSettingsBase):
    """Create sync settings."""
    pass


class SyncSettingsUpdate(BaseModel):
    """Update sync settings."""
    sync_interval_minutes: Optional[int] = None
    is_enabled: Optional[bool] = None


class SyncSettingsRead(SyncSettingsBase):
    """Read sync settings with status."""
    id: int
    last_synced_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
