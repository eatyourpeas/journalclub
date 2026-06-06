```markdown
# Podcast Dialog Instructions

You will create a short conversational podcast-style dialog between two speakers about the paper.

Roles:
- `host`: introduces the paper, frames the topic, and asks clarifying or follow-up questions.
- `guest`: summarizes findings, explains methods succinctly, and answers the host's questions.

Requirements:
- Start with a brief host introduction (title, source, lead author) of 1-2 sentences.
- Produce a dialog of approximately 8-12 turns total (both speakers combined).
- Keep each turn short (one or two sentences) and conversational.
- The host should ask explicit questions and the guest should answer them naturally.
- The discussion MUST clearly cover all of the following in order:
  1) study objective or research question
  2) key results/findings
  3) authors' conclusions/interpretation
  4) a plain-language take-home message for clinicians/readers
- Include at least one host challenge or clarification question (for example: "How strong is this evidence?" or "What should clinicians do with this?").
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
