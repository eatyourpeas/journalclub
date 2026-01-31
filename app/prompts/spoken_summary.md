```markdown
# Spoken Summary Instructions

Produce a concise spoken summary of the paper suitable for a brief audio segment.

- Objectives:
- Provide a short introduction (1 sentence) with paper title and lead author/source.
- Clearly state the key assumptions and objectives of the study.
- Summarise the main findings/results in 2-4 sentences.
- State the conclusions and implications in 1-2 sentences.
- Keep it listener-friendly and avoid technical jargon where possible.
- Skip author lists, references, equations, figures, and tables.

Do NOT use hedging phrases such as "appears to be", "seems to be", "may", or "might".
Only mention the lead author (single name) in the introduction; do NOT list all authors.

OUTPUT FORMAT:
Return exactly one JSON object with a single key `script` containing the spoken summary text.

Example:
```json
{"script":"This study, titled 'XYZ', from Journal A (lead author Smith), investigates ... Key assumptions were ... The main findings were ... In conclusion ..."}
```
```
