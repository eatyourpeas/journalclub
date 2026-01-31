# API Reference

Complete documentation of all available endpoints.

## Papers

### Upload Paper
```http
POST /api/papers/upload
Content-Type: multipart/form-data

file: <PDF file>
```

**Response:**
```json
{
  "filename": "example.pdf",
  "file_path": "/uploads/example.pdf",
  "text_preview": "First 500 characters...",
  "total_pages": 12,
  "word_count": 5432,
  "status": "parsed",
  "expires_at": "2026-01-31T10:30:00"
}
```

### Get Paper Info
```http
GET /api/papers/{filename}
```

### Summarize Paper
```http
POST /api/papers/summarise
Content-Type: application/json

{
  "filename": "example.pdf"
}
```

**Response:**
```json
{
  "task_id": "abc123...",
  "status": "pending",
  "filename": "example.pdf"
}
```

### Get Summary Status
```http
GET /api/papers/summarise/{task_id}
```

### Generate TTS Script
```http
POST /api/papers/tts-script
Content-Type: application/json

{
  "filename": "example.pdf"
}
```

### Read Aloud (Single Paper)
```http
POST /api/papers/read_aloud
Content-Type: application/json

{
  "filename": "example.pdf"
}
```

Returns: Audio stream (audio/mpeg)

## Topics

### Create Topic
```http
POST /api/papers/topics
Content-Type: application/json

{
  "topic_name": "My Research Topic",
  "filenames": ["paper1.pdf", "paper2.pdf"]
}
```

### List All Topics
```http
GET /api/papers/topics
```

### Read Topic Aloud
```http
GET /api/papers/topics/{topic_id}/read_aloud
```

Returns: Audio stream (audio/mpeg)

### Delete Topic
```http
DELETE /api/papers/topics/{topic_id}
```

### List Active Papers
```http
GET /api/papers/active
```

Returns list of all uploaded papers that haven't expired.

## RSS Feed

### Get Podcast Feed
```http
GET /api/papers/podcast.rss
```

Returns: RSS/XML podcast feed