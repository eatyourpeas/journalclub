```markdown
# Podcast Dialog Instructions

You will create a short conversational podcast-style dialog between two speakers about the paper.

Roles:
- `host`: introduces the paper, frames the topic, and asks clarifying or follow-up questions.
- `guest`: summarizes findings, explains methods succinctly, and answers the host's questions.

Requirements:
- Start with a brief host introduction (title, source, lead author) of 1-2 sentences.
- Produce a dialog of approximately 6-12 turns total (both speakers combined).
- Keep each turn short (one or two sentences) and conversational.
- Avoid references, author lists, equations, figures, and hedging phrases.

OUTPUT FORMAT (REQUIRED):
Return exactly one JSON object and nothing else. The JSON MUST contain a key `dialog` whose value is an array of turn objects.
Each turn object must contain `speaker` (either "host" or "guest") and `text`.

Example:
```json
{"dialog":[{"speaker":"host","text":"This study, titled 'XYZ'..."},{"speaker":"guest","text":"The authors found..."}]}
```

If you cannot follow these instructions, return an empty JSON object: `{}`.
```
