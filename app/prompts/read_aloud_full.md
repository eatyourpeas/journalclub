```markdown
# Read-Aloud (Full Paper) Instructions

You will produce a natural audio script that reads the paper verbatim but formatted for listening.

Rules:
- Begin with a brief spoken introduction (1-2 sentences) that includes: the paper title, the publication source (journal or preprint server if available), and the lead author name (use 'the lead author' if not explicit).
- After the introduction, read the paper content in a linear, listener-friendly way.
- Skip keywords, author lists, affiliations (except the single lead author mention in the intro), references, acknowledgments, and figure/table callouts. Please also skip the abstract.
- Do NOT use hedging phrases such as "appears to be", "seems to be", or "may" to introduce the paper.
- Keep sentences natural and complete; convert acronyms on first use.

OUTPUT FORMAT:
Return exactly one JSON object with a single key `script` containing the full audio script string.

Example:
```json
{"script":"This study, titled 'XYZ', published in Journal A, by the lead author Smith, investigates ... <full script>"}
```
``` 
