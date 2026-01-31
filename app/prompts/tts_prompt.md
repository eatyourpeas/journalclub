# Text-to-Speech Script Generation Instructions

You are creating an audio script for a research paper that will be read aloud using text-to-speech.

Your task is to transform this research paper into a natural, easy-to-listen script. Follow these rules:

## 1. START with a brief introduction (2-3 sentences) that includes:

- The paper title
- Main topic/purpose based on the abstract
- Key finding or contribution
- Begin with a phrase that introduces the content and subject. For example: "This paper, entitled "Safety and pharmacokinetics of teplizumab in children less than 8 years of age with stage 2 type 1 diabetes", discusses monoclonal immuntherapies in the management of symptomatic type 1 diabetes. 

## 2. SKIP entirely:

- Keywords section
- Author names and affiliations
- References section
- Acknowledgments
- In-text citations like [1], [2], (Smith et al., 2023)
- Figure and table descriptions (e.g., "See Figure 1", "Table 2 shows...")
- Mathematical equations and formulas

## 3. SKIP the abstract section when reading the main body

Since you already used it in the introduction, don't read it again in the body.

## 4. For the MAIN CONTENT:

- Read the Introduction, Methods, Results, Discussion, and Conclusion sections
- Use natural transitions between sections (e.g., "In the methods section...")
- Simplify overly technical phrases when possible
- Maintain the key scientific concepts and findings
- Use "the authors" or "the researchers" instead of specific names

## 5. FORMATTING for audio:

- Write in complete, natural sentences
- Use transitions like "The results show that...", "Interestingly...", "In conclusion..."
- Avoid parenthetical asides
- Convert acronyms to full words on first use (e.g., "Machine Learning, or ML")
- Do not include any stage directions or any details of production.
- Following on from summarising the paper, then proceed to reading the paper, without the abstract and the references.
- Avoid phrases like 'this paper appears to say'
- Do not read out punctuation (for example asterisk)

## 6. FORBIDDEN PHRASES

- Do NOT use hedging or tentative phrases such as: "appears to be", "seems to be", "may", "might", "appears" at the start of the introduction or summary.
- Do NOT introduce the paper using phrasing like "this paper appears to be about" or "this paper seems to".

## 7. OUTPUT FORMAT (REQUIRED)

Return exactly one JSON object and nothing else. The JSON must contain a single key named "script" whose value is the full audio script as a single string. Example:

```json
{"script":"<Begin audio script here...>"}
```

The model must not output any additional text, analysis, or metadata outside the JSON object. If you cannot follow these instructions, return an empty JSON object: `{}`.

## 8. EXAMPLE INTRODUCTION

Start the audio with a concise natural introduction of 1-2 sentences. Example (follow this tone, not verbatim):

"This study, titled 'Title Here', investigates [main topic]. The key finding is that [one-line key finding]."

Do not include author names or affiliations in the introduction. Use 'the authors' or 'the researchers' where needed.
