# Leave Management System - PDF/File Attachment Implementation Summary

## What Was Added

### 1. Database Layer (Models)

**Updated LeaveType Model:**

- `requires_document: Boolean` - Flag if documents required
- `document_description: Text` - What documents needed
- `allowed_file_types: String` - CSV of allowed extensions

**New LeaveAttachment Model:**

- Complete file storage and tracking system
- Links to LeaveTransaction (one-to-many)
- Tracks uploader, size, type, extension
- Timestamp of upload

### 2. File Management Service

**New File Manager (`app/core/file_manager.py`):**

- File validation (type, size)
- Secure file storage
- File retrieval and deletion
- MIME type detection
- Configuration for upload directory and limits

### 3. CRUD Operations

**New LeaveAttachmentCRUD:**

- Create attachments
- Read by ID and transaction
- Update descriptions
- Delete files and records

### 4. API Endpoints (6 new endpoints)

```
POST   /attachments                      - Upload file
GET    /applications/{id}/attachments    - List attachments
GET    /attachments/{id}                 - Get details
GET    /attachments/{id}/download        - Download file
PATCH  /attachments/{id}                 - Update description
DELETE /attachments/{id}                 - Delete file
```

### 5. Pydantic Schemas

**New Schemas:**

- `LeaveAttachmentCreate` - For uploading
- `LeaveAttachmentRead` - For responses
- `LeaveTransactionWithAttachmentsRead` - Complete view

**Updated Schemas:**

- `LeaveTypeCreate/Update/Read` - Added document fields

### 6. Frontend Widgets

**LEAVE_ATTACHMENTS_FRONTEND.html includes:**

- Leave Type Configuration with document requirements
- Leave Application Form with drag-drop upload
- Application View with file listing and download
- File validation and display
- Document requirement alerts

---

## Implementation Steps

### Step 1: Update Database

Run the migration:

```bash
cd c:\Users\ehsan javed\Desktop\ehsan\HRMS\backend
alembic upgrade head
```

Or manually create the tables using the migration file:

```bash
# Run this in your terminal
python -c "
from app.core.database import engine
from app.models.Leaves import Base
Base.metadata.create_all(bind=engine)
"
```

### Step 2: Verify Files Created

Check these files exist:

- ✅ `app/core/file_manager.py` - File handling
- ✅ `app/crud/leave.py` - Updated with LeaveAttachmentCRUD
- ✅ `app/schemas/leave.py` - Updated schemas
- ✅ `app/api/v1/leaves.py` - Updated with attachment endpoints
- ✅ `app/models/Leaves.py` - Updated models
- ✅ `alembic/versions/add_leave_attachments.py` - Migration file

### Step 3: Create Upload Directory

```bash
# Create uploads directory
mkdir -p uploads/leave_attachments
```

### Step 4: Update Main App

Add to `app/main.py`:

```python
from app.api.v1 import leaves

# Make sure router is included
app.include_router(leaves.router)
```

### Step 5: Test API Endpoints

```bash
# 1. Create a leave type with documents required
curl -X POST http://localhost:8000/api/v1/leaves/types \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "cycle_id": 1,
    "name": "Medical Leave",
    "requires_document": true,
    "document_description": "Medical certificate from hospital",
    "allowed_file_types": "pdf,jpg,png",
    "total_per_cycle": 10
  }'

# 2. Apply for leave
curl -X POST http://localhost:8000/api/v1/leaves/applications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "employee_id": 5,
    "leave_type_id": 1,
    "cycle_id": 1,
    "employee_record_id": 1,
    "start_date": "2024-02-20",
    "end_date": "2024-02-22",
    "requested_days": 3
  }'

# 3. Upload file (replace 1 with actual application ID)
curl -X POST http://localhost:8000/api/v1/leaves/applications/1/attachments \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@medical_certificate.pdf" \
  -F "description=Medical certificate"

# 4. Get attachments
curl http://localhost:8000/api/v1/leaves/applications/1/attachments \
  -H "Authorization: Bearer YOUR_TOKEN"

# 5. Download file
curl http://localhost:8000/api/v1/leaves/attachments/1/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o downloaded_file.pdf
```

### Step 6: Configure Frontend

Use the HTML file `LEAVE_ATTACHMENTS_FRONTEND.html` as a template for:

- Leave type setup form
- Application form with file upload
- Application viewing with downloads

---

## Feature Breakdown

### 1. Document Requirements by Leave Type

**Design:**

- Admin configures which leave types need documents
- Specify what documents are needed
- Define allowed file types

**Example:**

```
Leave Type: Maternity Leave
- Requires Document: Yes
- Description: Medical certificate from doctor
- Allowed Types: PDF, JPG, PNG
```

**UI:**

- Checkbox: "Requires Document"
- Text field: "What documents needed?"
- Input: "Allowed file types (comma-separated)"

### 2. File Upload in Applications

**Design:**

- Drag & drop upload area
- Multiple file support
- Real-time validation
- File preview before submit

**Validation:**

- Check against leave type's allowed_file_types
- Max 10 MB per file
- MIME type detection

**Workflow:**

1. Employee starts leave application
2. System checks if documents required
3. Show document requirement info
4. Provide upload area
5. File validated
6. Upload to server
7. Record stored in database

### 3. File Management

**Storage:**

- Files stored in `uploads/leave_attachments/`
- Unique naming: `transaction_ID_emp_ID_timestamp.ext`
- Safe isolation from web root

**Access:**

- Download via API endpoint
- Only authorized users
- Secure file serving

**Cleanup:**

- Delete when application deleted
- Cascade delete via foreign keys
- Manual cleanup option

### 4. Tracking & Audit

**Tracked Information:**

- Who uploaded (uploaded_by)
- When uploaded (uploaded_at)
- Original filename
- File size
- File type/extension
- Optional description

**Queries Available:**

- Get attachments by application
- Get attachments by uploader
- Get attachments by date range
- Get file usage statistics

---

## API Usage Examples

### JavaScript/Fetch

```javascript
// Upload file
const uploadFile = async (applicationId, file, description) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("description", description);

  const response = await fetch(
    `/api/v1/leaves/applications/${applicationId}/attachments`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    },
  );

  return await response.json();
};

// Get attachments
const getAttachments = async (applicationId) => {
  const response = await fetch(
    `/api/v1/leaves/applications/${applicationId}/attachments`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  return await response.json();
};

// Download attachment
const downloadAttachment = (attachmentId) => {
  const link = document.createElement("a");
  link.href = `/api/v1/leaves/attachments/${attachmentId}/download`;
  link.setAttribute("download", "");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
```

### React Component Example

```jsx
import React, { useState } from "react";

export function LeaveApplicationForm() {
  const [files, setFiles] = useState([]);
  const [documentRequired, setDocumentRequired] = useState(false);

  const handleFileSelect = (e) => {
    setFiles([...files, ...Array.from(e.target.files)]);
  };

  const handleUpload = async (applicationId) => {
    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `/api/v1/leaves/applications/${applicationId}/attachments`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        },
      );

      if (response.ok) {
        console.log("File uploaded successfully");
      }
    }
  };

  return (
    <div>
      <input type="file" multiple onChange={handleFileSelect} />
      <button onClick={() => handleUpload(1)}>Upload</button>
      <ul>
        {files.map((f, i) => (
          <li key={i}>{f.name}</li>
        ))}
      </ul>
    </div>
  );
}
```

---

## Configuration Options

### File Manager Settings

```python
# In app/core/file_manager.py

UPLOAD_DIR = "uploads/leave_attachments"    # Change this path
MAX_FILE_SIZE = 10 * 1024 * 1024           # 10 MB, adjust as needed
ALLOWED_EXTENSIONS = {
    "pdf", "jpg", "jpeg", "png",
    "doc", "docx", "xls", "xlsx"
    # Add more as needed
}
```

### Per Leave Type Settings

```python
# When creating a leave type
{
    "name": "Medical Leave",
    "allowed_file_types": "pdf,jpg,png",  # Override global defaults
    "requires_document": true,
    "document_description": "..."
}
```

---

## Security Checklist

✅ File type validation
✅ File size limits
✅ MIME type checking
✅ Unique file naming
✅ Storage outside web root
✅ Permission checks on download/delete
✅ User authentication required
✅ Cascade deletion with transaction
✅ No execution permission on uploads
✅ Virus scanning ready (future)

---

## Performance Considerations

- Files stored on disk (not in database)
- Database only stores metadata
- Lazy loading of attachments
- Indexes on transaction_id and uploaded_by
- Cleanup migration for old files
- Chunked upload for large files (future)

---

## Troubleshooting

### Issue: File upload fails

**Solution:**

- Check `uploads/leave_attachments/` directory exists
- Verify write permissions
- Check MAX_FILE_SIZE setting
- Validate file type matches allowed_file_types

### Issue: Download returns 404

**Solution:**

- Verify file path in database
- Check file exists on disk
- Verify user permissions
- Check file wasn't deleted

### Issue: File type not in allowed list

**Solution:**

- Update `allowed_file_types` in leave type
- Adjust global ALLOWED_EXTENSIONS
- Clear browser cache and retry

---

## Next Enhancements

1. **Virus Scanning**

   ```python
   import pyclamav
   # Scan uploaded files before storage
   ```

2. **File Preview**
   - PDF preview
   - Image preview
   - Document preview

3. **Batch Operations**
   - Bulk download as ZIP
   - Batch delete
   - Export with files

4. **Email Integration**
   - Email notification with file
   - Email reminders for required docs

5. **Access Logging**
   - Log who downloaded what
   - Audit trail

6. **Versioning**
   - Keep file history
   - Version control for edits

7. **Advanced Storage**
   - S3/Cloud storage
   - CDN integration
   - Backup strategy

---

## Files Summary

| File                                        | Purpose                   |
| ------------------------------------------- | ------------------------- |
| `app/models/Leaves.py`                      | LeaveAttachment model     |
| `app/schemas/leave.py`                      | LeaveAttachment schemas   |
| `app/crud/leave.py`                         | LeaveAttachmentCRUD class |
| `app/core/file_manager.py`                  | File handling service     |
| `app/api/v1/leaves.py`                      | Attachment endpoints      |
| `alembic/versions/add_leave_attachments.py` | Database migration        |
| `LEAVE_ATTACHMENTS_GUIDE.md`                | Complete documentation    |
| `LEAVE_ATTACHMENTS_FRONTEND.html`           | UI widgets                |

---

## Support

For issues or questions:

1. Check the LEAVE_ATTACHMENTS_GUIDE.md
2. Review error messages in logs
3. Test endpoints with Postman
4. Verify database migration ran
5. Check file permissions

---
