import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException, status

# Configuration
UPLOAD_DIR = "uploads/leave_attachments"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"}

class FileManagementService:
    """Service for handling file uploads, storage, and downloads"""

    @staticmethod
    def ensure_upload_directory():
        """Create upload directory if it doesn't exist"""
        Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_file(file: UploadFile, allowed_types: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate uploaded file
        Returns: (is_valid, error_message)
        """
        if allowed_types is None:
            allowed_types = ",".join(ALLOWED_EXTENSIONS)
        
        # Check file type
        allowed = [ext.lower() for ext in allowed_types.split(",")]
        file_ext = file.filename.split(".")[-1].lower()
        
        if file_ext not in allowed:
            return False, f"File type '{file_ext}' not allowed. Allowed: {allowed_types}"
        
        # Check file size
        if file.size and file.size > MAX_FILE_SIZE:
            return False, f"File size exceeds {MAX_FILE_SIZE / (1024*1024):.1f} MB limit"
        
        return True, ""

    @staticmethod
    async def save_file(
        file: UploadFile, 
        transaction_id: int, 
        employee_id: int
    ) -> Tuple[str, str, int]:
        """
        Save uploaded file
        Returns: (file_path, file_name, file_size)
        """
        FileManagementService.ensure_upload_directory()
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = file.filename.split(".")[-1]
        unique_filename = f"transaction_{transaction_id}_emp_{employee_id}_{timestamp}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            return file_path, unique_filename, len(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving file: {str(e)}"
            )

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete a file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
            return False

    @staticmethod
    def get_file_type(filename: str) -> str:
        """Get MIME type of file"""
        ext = filename.split(".")[-1].lower()
        mime_types = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return mime_types.get(ext, "application/octet-stream")

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension"""
        return filename.split(".")[-1].lower() if "." in filename else ""

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes"""
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return 0
