# Creating Topics

Topics allow you to combine up to 5 related papers into a single audio episode with smooth transitions between papers.

## Why Use Topics?

- **Coherent Narrative** - The AI creates natural segues between papers
- **Deep Dives** - Explore a specific area of research comprehensively
- **Efficient Learning** - Listen to multiple perspectives on a topic in one session

## How to Create a Topic

### Via API
```bash
POST /api/papers/topics
Content-Type: application/json

{
  "topic_name": "COVID-19 Vaccine Efficacy",
  "filenames": [
    "pfizer-study.pdf",
    "moderna-study.pdf",
    "astrazeneca-study.pdf"
  ]
}
```

**Response:**
```json
{
  "topic_id": "abc123...",
  "topic_name": "COVID-19 Vaccine Efficacy",
  "filenames": ["pfizer-study.pdf", "moderna-study.pdf", "astrazeneca-study.pdf"],
  "status": "created",
  "expires_at": "2026-01-31T10:30:00"
}
```

### Listening to Your Topic

Once created, you can:

1. **Listen directly** via `/api/papers/topics/{topic_id}/read_aloud`
2. **Subscribe to RSS** and find it in your podcast feed
3. **View all topics** via `/api/papers/topics`

## Limitations

- Maximum 5 papers per topic
- Topics expire after 24 hours
- All papers must be uploaded before creating the topic

## Tips for Great Topics

- Choose papers with related themes or complementary findings
- Mix different research methodologies for diverse perspectives
- Keep papers of similar length for balanced audio duration