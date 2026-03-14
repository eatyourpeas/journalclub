# Frequently Asked Questions

## General

**Q: How long are my papers stored?**  
A: All uploaded papers and created topics are automatically deleted after 24 hours. This gives you plenty of time to listen on your commute while keeping the service lightweight.

**Q: What happens if the server restarts?**  
A: Since we don't use persistent storage, all data is lost on restart. This is by design - the service is meant for temporary, on-demand use.

**Q: Can I share my topics with others?**  
A: Not currently. Each topic is tied to your session and expires after 24 hours.

## Papers

**Q: What file formats are supported?**  
A: Currently only PDF files are supported.

**Q: Is there a file size limit?**  
A: Yes, the recommended maximum is 10MB per PDF.

**Q: Can I upload multiple papers at once?**  
A: Yes! Upload up to 5 papers, then create a topic to combine them.

## Audio & Summarization

**Q: How long does it take to generate audio?**  
A: Typically 15–40 seconds for a standard paper. The AI needs to:

1. Generate an optimized script (15–30s)
2. Convert to audio via edge-tts (~5–15s)

**Q: Can I download the audio?**  
A: Yes! Right-click the audio player and select "Download" or use the RSS feed to sync to your podcast app.

**Q: What voice is used for narration?**  
A: We use Microsoft Edge neural TTS (`edge-tts`). The default voices are `en-GB-RyanNeural` (male host) and `en-GB-SoniaNeural` (female co-host). These are high-quality neural voices and require no API key. You can override them with the `EDGE_TTS_VOICE_MALE` and `EDGE_TTS_VOICE_FEMALE` environment variables.

## Topics

**Q: Why is there a 5-paper limit for topics?**  
A: To keep audio episodes at a reasonable length (typically 30-60 minutes) and ensure good performance.

**Q: Can I edit a topic after creating it?**  
A: Not currently. You'll need to delete and recreate it.

## RSS Feed

**Q: Why don't I see my individual papers in the RSS feed?**  
A: The feed currently only shows topics (collections of papers). Create a topic with just one paper if you want it in your podcast feed.

**Q: My podcast app says the feed is invalid**  
A: Make sure you're using the full URL including `https://` and that topics exist in your feed.

## Technical

**Q: What AI model do you use?**  
A: The service uses a configurable LLM backend for summarization and script generation.

**Q: Is my data private?**  
A: Yes - papers are only stored temporarily on the server and are not shared with anyone. They're automatically deleted after 24 hours.

**Q: Can I self-host this?**  
A: Yes! The codebase is designed to run on any server with Python and FastAPI.