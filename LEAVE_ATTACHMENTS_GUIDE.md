# Leave Management System - PDF/File Attachment Features

## Overview

Complete file attachment system for leave applications with the following features:

✅ **Document Requirements by Leave Type** - Define which leave types need supporting documents
✅ **File Upload** - Employees can upload PDFs, images, and documents
✅ **File Download** - Generate direct download links for attachments
✅ **File Validation** - Validate file type and size
✅ **Storage Management** - Secure file storage system
✅ **Attachment Tracking** - Track who uploaded what and when

---

## Database Changes

### New Fields in LeaveType Model

```python
requires_document: Boolean          # Whether documents are required
document_description: Text          # What documents are needed (e.g., "Medical certificate")
allowed_file_types: String(255)    # Comma-separated allowed extensions
```

### New LeaveAttachment Model

```python
id: Integer (Primary Key)
transaction_id: Integer (Foreign Key → LeaveTransaction)
file_name: String(255)             # Original filename
file_path: String(500)             # Path to stored file
file_size: Integer                 # Size in bytes
file_type: String(50)              # MIME type (application/pdf, image/jpeg, etc.)
file_extension: String(20)         # File extension (.pdf, .jpg, etc.)
description: Text                  # Optional description
uploaded_by: Integer (FK → Employee)
uploaded_at: DateTime              # Timestamp of upload
```

---

## API Endpoints

### File Upload

```
POST /api/v1/leaves/applications/{application_id}/attachments
Content-Type: multipart/form-data

Parameters:
- file: UploadFile (REQUIRED)
- description: str (Optional)

Response: LeaveAttachmentRead
```

**Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/leaves/applications/1/attachments" \
  -H "Authorization: Bearer {token}" \
  -F "file=@medical_certificate.pdf" \
  -F "description=Medical certificate from Dr. Smith"
```

### Get Application Attachments

```
GET /api/v1/leaves/applications/{application_id}/attachments

Response: List[LeaveAttachmentRead]
```

### Get Attachment Details

```
GET /api/v1/leaves/attachments/{attachment_id}

Response: LeaveAttachmentRead
```

### Download File

```
GET /api/v1/leaves/attachments/{attachment_id}/download

Response: File (binary)
```

### Update Attachment Description

```
PATCH /api/v1/leaves/attachments/{attachment_id}

Body:
{
  "description": "Updated description"
}

Response: LeaveAttachmentRead
```

### Delete Attachment

```
DELETE /api/v1/leaves/attachments/{attachment_id}

Response: 204 No Content
```

---

## Configuration

### File Storage Settings

Located in `app/core/file_manager.py`:

```python
UPLOAD_DIR = "uploads/leave_attachments"  # Upload directory
MAX_FILE_SIZE = 10 * 1024 * 1024         # 10 MB limit
ALLOWED_EXTENSIONS = {                   # Default allowed types
    "pdf", "jpg", "jpeg", "png",
    "doc", "docx", "xls", "xlsx"
}
```

---

## Leave Type Setup Examples

### Example 1: Medical Leave (With Documents Required)

```json
{
  "name": "Medical Leave",
  "cycle_id": 1,
  "total_per_cycle": 10,
  "is_paid": true,
  "requires_document": true,
  "document_description": "Medical certificate from registered medical practitioner",
  "allowed_file_types": "pdf,jpg,png,doc,docx"
}
```

### Example 2: Bereavement Leave (With Documents)

```json
{
  "name": "Bereavement Leave",
  "cycle_id": 1,
  "total_per_cycle": 3,
  "is_paid": true,
  "requires_document": true,
  "document_description": "Death certificate or cremation certificate",
  "allowed_file_types": "pdf,jpg,png"
}
```

### Example 3: Casual Leave (No Documents)

```json
{
  "name": "Casual Leave",
  "cycle_id": 1,
  "total_per_cycle": 12,
  "is_paid": true,
  "requires_document": false,
  "allowed_file_types": "pdf,jpg,png,doc,docx"
}
```

---

## Frontend Integration

### 1. Leave Type Configuration Widget

Display document requirements UI:

```html
<!-- Checkbox for "Requires Documents" -->
<!-- Conditional fields for description and allowed types -->
```

### 2. Leave Application Form Widget

Enhanced with file upload:

```html
<!-- Drag & drop zone for files -->
<!-- File preview before upload -->
<!-- Multiple file selection -->
<!-- Document requirement alert -->
```

### 3. Application View Widget

Display attached files:

```html
<!-- File list for each application -->
<!-- Download links -->
<!-- File details (name, size, upload date) -->
```

---

## Upload Workflow

```
1. Employee selects leave type
2. System checks if documents required
3. Show document requirement info
4. Provide drag-drop upload area
5. Validate file type/size
6. Upload to server
7. Return attachment info
8. Display in application
```

---

## File Naming Convention

Files are stored with unique names to prevent conflicts:

```
transaction_{transaction_id}_emp_{employee_id}_{timestamp}.{extension}

Example: transaction_5_emp_123_20240215_103045.pdf
```

---

## Validation Rules

| Aspect             | Validation                                   |
| ------------------ | -------------------------------------------- |
| File Type          | Must match allowed_file_types for leave type |
| File Size          | Max 10 MB per file (configurable)            |
| Multiple Files     | Allowed (number not limited)                 |
| Empty Files        | Rejected                                     |
| Special Characters | Sanitized in storage                         |

---

## Security Features

✅ **File Type Validation** - Only allowed extensions
✅ **Size Limits** - Max 10 MB per file
✅ **Access Control** - Only uploader/HR can download
✅ **Unique Filenames** - Prevents overwrites
✅ **Storage Path** - Outside web root for security
✅ **Permission Checks** - Verified on download/delete

---

## Error Handling

| Error                   | Code | Cause             | Solution                  |
| ----------------------- | ---- | ----------------- | ------------------------- |
| File type not allowed   | 400  | Wrong extension   | Check allowed_file_types  |
| File size exceeds limit | 400  | File too large    | Upload smaller file       |
| Application not found   | 404  | Invalid ID        | Verify application exists |
| Attachment not found    | 404  | File deleted      | Re-upload                 |
| Not allowed to update   | 403  | Permission denied | Only uploader can edit    |
| Not allowed to delete   | 403  | Permission denied | Only uploader can delete  |

---

## Frontend Examples

### Upload Single File

```javascript
// Using FormData
const formData = new FormData();
formData.append("file", fileInput.files[0]);
formData.append("description", "Medical certificate");

const response = await fetch(`/api/v1/leaves/applications/1/attachments`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: formData,
});
```

### Upload Multiple Files

```javascript
// Loop through files
for (const file of fileInput.files) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("description", `Document: ${file.name}`);

  await fetch(`/api/v1/leaves/applications/1/attachments`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
}
```

### Download Attachment

```javascript
// Create download link
const downloadUrl = `/api/v1/leaves/attachments/123/download`;
const a = document.createElement("a");
a.href = downloadUrl;
a.setAttribute("download", "");
a.click();
```

### Display Files in React

```jsx
{
  application.attachments &&
    application.attachments.map((file) => (
      <div key={file.id} class="file-item">
        <p>{file.file_name}</p>
        <p>{(file.file_size / 1024).toFixed(2)} KB</p>
        <a href={`/api/v1/leaves/attachments/${file.id}/download`}>Download</a>
      </div>
    ));
}
```

---

## Database Migration

Create migration file to add new columns:

```python
# In migrations/versions/xxx_add_leave_attachments.py

def upgrade():
    op.add_column('leave_types', sa.Column('requires_document', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('leave_types', sa.Column('document_description', sa.Text(), nullable=True))
    op.add_column('leave_types', sa.Column('allowed_file_types', sa.String(255), server_default='pdf,jpg,png,doc,docx'))

    op.create_table(
        'leave_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_extension', sa.String(20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=func.now()),
        sa.ForeignKeyConstraint(['transaction_id'], ['leave_transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['employees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
```

---

## Testing Endpoints

### Create Leave Type with Documents

```bash
curl -X POST http://localhost:8000/api/v1/leaves/types \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "cycle_id": 1,
    "name": "Medical Leave",
    "requires_document": true,
    "document_description": "Medical certificate required",
    "allowed_file_types": "pdf,jpg,png",
    "total_per_cycle": 10
  }'
```

### Apply for Leave

```bash
curl -X POST http://localhost:8000/api/v1/leaves/applications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "employee_id": 5,
    "leave_type_id": 1,
    "cycle_id": 1,
    "employee_record_id": 1,
    "start_date": "2024-02-20",
    "end_date": "2024-02-22",
    "requested_days": 3,
    "employee_note": "Medical treatment"
  }'
```

### Upload File

```bash
curl -X POST http://localhost:8000/api/v1/leaves/applications/1/attachments \
  -H "Authorization: Bearer {token}" \
  -F "file=@medical_certificate.pdf" \
  -F "description=Medical certificate from hospital"
```

### Get Attachments

```bash
curl http://localhost:8000/api/v1/leaves/applications/1/attachments \
  -H "Authorization: Bearer {token}"
```

### Download File

```bash
curl http://localhost:8000/api/v1/leaves/attachments/1/download \
  -H "Authorization: Bearer {token}" \
  -o downloaded_file.pdf
```

---

## Cleanup and Maintenance

### Delete Old Attachments

```python
def cleanup_old_attachments(db: Session, days: int = 90):
    """Delete attachments older than X days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    old_attachments = db.query(LeaveAttachment).filter(
        LeaveAttachment.uploaded_at < cutoff_date
    ).all()

    for attachment in old_attachments:
        FileManagementService.delete_file(attachment.file_path)
        db.delete(attachment)

    db.commit()
```

---

## Next Steps

1. Run database migration to add new tables/columns
2. Test file upload with Postman/Insomnia
3. Integrate frontend widgets into your React/Vue app
4. Configure file storage path (production)
5. Add email notifications with attachment info
6. Implement virus scanning for uploaded files
7. Add file preview functionality
8. Create batch download feature (ZIP)

---

## Support for Different Leave Types

- **Medical Leave** → PDF, JPG, PNG (medical certificates)
- **Bereavement Leave** → PDF (death certificate)
- **Marriage Leave** → PDF (invitation/certificate)
- **Maternity Leave** → PDF (medical reports)
- **Casual Leave** → No documents required
- **Emergency Leave** → Documentation as proof

---
