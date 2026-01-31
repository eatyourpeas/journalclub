import httpx
import json
import re
import os
from typing import Optional, List, Any


class LLMService:
    """Service for interacting with Ollama LLM"""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL")
        self.api_key = os.getenv("OLLAMA_API_KEY")
        self.model = os.getenv("OLLAMA_MODEL")

        if not all([self.base_url, self.model]):
            raise ValueError("OLLAMA_BASE_URL and OLLAMA_MODEL must be set")

    async def call_llm(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1500,
    ):
        """Helper to call the chat completions endpoint and return the assistant content."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Ocp-Apim-Subscription-Key"] = self.api_key

                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )

        except httpx.HTTPError as e:
            raise Exception(f"LLM API error (call_llm): {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling LLM (call_llm): {str(e)}")

    async def summarise_paper(
        self, paper_text: str, metadata: Optional[dict] = None
    ) -> dict:
        """Generate a summary of an academic paper"""

        # If metadata is provided, include a system-level instruction to prefer metadata
        # as canonical and avoid repeating metadata fields in the generated summary.
        meta_instruction = ""
        if metadata:
            try:
                meta_json = json.dumps(metadata)
                meta_instruction = (
                    "Metadata (for context only): " + meta_json + "\n"
                    "Do NOT repeat or list the metadata fields (title, authors, doi, year, journal) in the summary; "
                    "use them only as background context when analyzing the paper.\n\n"
                )
            except Exception:
                meta_instruction = ""

        prompt = f"""{meta_instruction}Please analyze this academic paper and provide:
1. A concise summary (2-3 paragraphs)
2. Key findings and contributions (as bullet points)
3. Methodology used
4. Main conclusions

Paper text:
{paper_text}

Respond with valid JSON using these exact keys: summary, key_points, methodology, conclusions"""

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                headers = {"Content-Type": "application/json"}

                if self.api_key:
                    headers["Ocp-Apim-Subscription-Key"] = self.api_key

                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": (
                            (
                                [{"role": "system", "content": meta_instruction}]
                                if meta_instruction
                                else []
                            )
                            + [{"role": "user", "content": prompt}]
                        ),
                        "stream": False,
                        "response_format": {"type": "json_object"},  # Enable JSON mode
                    },
                )

                response.raise_for_status()
                result = response.json()

                content = (
                    result.get("choices", [{}])[0].get("message", {}).get("content", "")
                )

                # Try direct parse first (should work with JSON mode)
                try:
                    summary_data = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: strip backticks if present
                    json_string = content.split("```")[0].strip()
                    if "```" in content:
                        # Extract from code block
                        match = re.search(
                            r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL
                        )
                        json_string = match.group(1) if match else json_string
                    summary_data = json.loads(json_string)

                return {"summary": summary_data, "model_used": self.model}

        except httpx.HTTPError as e:
            raise Exception(f"LLM API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling LLM: {str(e)}")

    async def summarise_paper_stream(self, paper_text: str):
        """
        Generate a summary of an academic paper with streaming response
        """
        # ... keep your existing streaming implementation ...
        pass

    async def generate_text_to_speech_script(
        self, paper_text: str, mode: str = "read_aloud", metadata: Optional[dict] = None
    ) -> Any:
        """Generate an optimized text-to-speech script from a research paper.

        mode: one of 'read_aloud'|'read_aloud_full'|'spoken_summary'|'podcast'
        Returns a string for script modes or a dict (e.g., {'dialog': [...]}) for podcast mode.
        """
        from pathlib import Path

        # Choose prompt file based on mode
        prompts_dir = Path(__file__).parent.parent / "prompts"
        if mode == "read_aloud_full":
            prompt_path = prompts_dir / "read_aloud_full.md"
        elif mode == "spoken_summary":
            prompt_path = prompts_dir / "spoken_summary.md"
        elif mode == "podcast":
            prompt_path = prompts_dir / "podcast_dialog.md"
        else:
            prompt_path = prompts_dir / "tts_prompt.md"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                tts_instructions = f.read()
            # Strip leading/trailing markdown code fences (```markdown / ```)
            tts_instructions = re.sub(r"^```[^\n]*\n", "", tts_instructions)
            tts_instructions = re.sub(r"\n```\s*$", "", tts_instructions)
        except FileNotFoundError:
            raise Exception(f"TTS prompt file not found at {prompt_path}")
        except Exception as e:
            raise Exception(f"Error reading TTS prompt file: {str(e)}")

        # Improve instruction adherence by sending TTS rules as a system message
        # If metadata exists, add a short metadata instruction so the model knows what's canonical
        meta_system = ""
        if metadata:
            try:
                meta_system = (
                    "Metadata (context only): " + json.dumps(metadata) + "\n"
                    "Do NOT read aloud or repeat fields present in the metadata (title, authors, doi, year, journal); "
                    "use them only as background context.\n\n"
                )
            except Exception:
                meta_system = ""

        system_message = (
            "You are a text-to-speech script generator. Follow these rules exactly when producing the script:\n"
            "- Start with a brief (2-3 sentence) introduction as described.\n"
            "- Skip keywords, author lists, references, citations, figures, tables, and equations.\n"
            "- Do not repeat the abstract in the body.\n"
            "- Produce natural, complete sentences suitable for audio.\n"
            "- Convert acronyms on first use.\n"
            "- Return ONLY the final audio script or the structured JSON the prompt requests. Do not include any analysis, step-by-step notes, or metadata.\n\n"
        ) + tts_instructions
        if meta_system:
            system_message = meta_system + system_message

        user_message = f"Please follow the system instructions and produce the requested output for mode '{mode}'.\n\nPaper text:\n\n{paper_text}"

        # Helper: sanitize script text to remove hedging and author/affiliation lists
        def _sanitize_script(text: str) -> str:
            if not text:
                return text

            s = text

            # Remove obvious introductory hedging sentences like 'The provided text appears to be...'
            try:
                s = re.sub(
                    r"(?im)^(?:the provided text|this text|the following text)[^\n]*\b(appears to be|appears|seems to be|seems|may be|might be|may|might)\b[^.\n]*[\.\n]",
                    "",
                    s,
                )
            except Exception:
                pass

            # Remove lines that look like an authors/affiliations list (numbered or 'Name - Affiliation')
            try:
                # Numbered lists like '1. Name - Affiliation' or '1) Name - Affiliation'
                s = re.sub(
                    r"(?m)^(\s*\d+[\.)]\s*[^\n]*(?:\n\s*\d+[\.)]\s*[^\n]*){2,}",
                    lambda m: _collapse_author_block(m.group(0)),
                    s,
                )
            except Exception:
                pass

            try:
                # Consecutive lines with 'Name - Institution'
                s = re.sub(
                    r"(?m)^(?:[^\n\r]+\s-\s[^\n\r]+\s*(?:\n|\r|$)){2,}",
                    lambda m: _collapse_author_block(m.group(0)),
                    s,
                )
            except Exception:
                pass

            # Remove explicit 'Authors:' blocks
            try:
                s = re.sub(r"(?im)^\s*authors?:\s*.*(?:\n\s*[-\d\w].*)*", "", s)
            except Exception:
                pass

            # Remove hedging phrases anywhere
            s = re.sub(
                r"(?i)\b(appears to be|appears|seems to be|seems|may be|might be|may|might)\b",
                "",
                s,
            )

            # Collapse multiple blank lines
            s = re.sub(r"\n{2,}", "\n\n", s)

            return s.strip()

        # Helper used by sanitize to collapse a block of author lines into a single lead-author sentence
        def _collapse_author_block(block: str) -> str:
            # Find first non-empty line and extract a name before '-' or ','
            try:
                for line in block.splitlines():
                    ln = line.strip()
                    if not ln:
                        continue
                    # Remove leading numbering
                    ln2 = re.sub(r"^\s*\d+[\.)]\s*", "", ln)
                    # Extract name before ' - ' or ' , '
                    if " - " in ln2:
                        name = ln2.split(" - ")[0].strip()
                    else:
                        name = ln2.split(",")[0].strip()
                    if name:
                        return f"The lead author is {name}."
            except Exception:
                pass
            return "The lead author is the first listed author."

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                headers = {"Content-Type": "application/json"}

                if self.api_key:
                    headers["Ocp-Apim-Subscription-Key"] = self.api_key

                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message},
                        ],
                        "stream": False,
                        "temperature": 0.0,
                        "max_tokens": 2500,
                    },
                )

                response.raise_for_status()
                result = response.json()

                # OpenAI/Ollama-compatible API response
                content = (
                    result.get("choices", [{}])[0].get("message", {}).get("content", "")
                )

                # Try to parse JSON output first (supports {"script":...} and {"dialog":[...]})
                def _try_parse_dialog(raw_text: str):
                    # Try direct JSON parse
                    try:
                        parsed = json.loads(raw_text)
                        if isinstance(parsed, dict) and "dialog" in parsed:
                            return parsed
                    except Exception:
                        pass

                    # Try to extract JSON code block containing the object
                    try:
                        m2 = re.search(
                            r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL
                        )
                        if m2:
                            p = json.loads(m2.group(1))
                            if isinstance(p, dict) and "dialog" in p:
                                return p
                    except Exception:
                        pass

                    # Try to find an inline JSON object
                    try:
                        m3 = re.search(
                            r"(\{\s*\"dialog\"\s*:\s*\[.*\]\s*\})", raw_text, re.DOTALL
                        )
                        if m3:
                            p = json.loads(m3.group(1))
                            if isinstance(p, dict) and "dialog" in p:
                                return p
                    except Exception:
                        pass

                    return None

                # If podcast mode requested, attempt to repair non-JSON outputs by retrying (nudge) up to 2 times
                if mode == "podcast":
                    parsed = _try_parse_dialog(content)
                    repair_attempts = 0
                    while parsed is None and repair_attempts < 2:
                        repair_attempts += 1
                        repair_prompt = (
                            "The previous assistant output did not return valid JSON. "
                            "Extract and return ONLY a single JSON object with key 'dialog' whose value is an array of turns. "
                            "Each turn must have 'speaker' and 'text'. If you cannot extract such JSON, return {}.\n\n"
                            "Previous output:\n" + content
                        )
                        # Use the same podcast instructions as the system message to improve adherence
                        try:
                            repaired = await self.call_llm(
                                repair_prompt,
                                system=tts_instructions,
                                temperature=0.0,
                                max_tokens=800,
                            )
                        except Exception:
                            repaired = None

                        if repaired:
                            parsed = _try_parse_dialog(repaired)
                            content = repaired

                    if parsed is not None:
                        # Clean each dialog turn and return
                        cleaned = {"dialog": []}
                        for turn in parsed.get("dialog", []):
                            text = turn.get("text", "")
                            # Use sanitizer to remove hedging and author lists
                            text = _sanitize_script(text)
                            # Collapse 'by A, B and C' -> 'by A'
                            m4 = re.search(
                                r"(?i)\\bby\\s+([^.\\n,]+?)(?:[,;]|\\sand\\b|\\s&\\s)",
                                text,
                            )
                            if m4:
                                first = m4.group(1).strip()
                                text = re.sub(
                                    r"(?i)\\bby\\s+[^.\\n]+",
                                    "by " + first,
                                    text,
                                    count=1,
                                )
                            cleaned["dialog"].append(
                                {"speaker": turn.get("speaker"), "text": text.strip()}
                            )
                        return cleaned
                else:
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict):
                            if "script" in parsed:
                                script_text = parsed["script"]
                                # Sanitize script: remove hedging and collapse author/affiliation lists
                                script_text = _sanitize_script(script_text)
                                return script_text.strip()
                            if "dialog" in parsed:
                                cleaned = {"dialog": []}
                                for turn in parsed.get("dialog", []):
                                    text = turn.get("text", "")
                                    # Remove hedging
                                    text = re.sub(
                                        r"(?i)\\b(appears to be|appears|seems to be|seems|may be|might be|may|might)\\b",
                                        "",
                                        text,
                                    )
                                    # Collapse author lists if present
                                    text = re.sub(
                                        r"(?im)^\\s*authors?:\\s*(.+)$",
                                        lambda m: "The lead author is "
                                        + m.group(1).split(",")[0].strip(),
                                        text,
                                    )
                                    m = re.search(
                                        r"(?i)\\bby\\s+([^.\\n,]+?)(?:[,;]|\\sand\\b|\\s&\\s)",
                                        text,
                                    )
                                    if m:
                                        first = m.group(1).strip()
                                        text = re.sub(
                                            r"(?i)\\bby\\s+[^.\\n]+",
                                            "by " + first,
                                            text,
                                            count=1,
                                        )
                                    cleaned["dialog"].append(
                                        {
                                            "speaker": turn.get("speaker"),
                                            "text": text.strip(),
                                        }
                                    )
                                return cleaned
                    except Exception:
                        pass

                # Fallback: if not JSON, attempt to extract script field embedded in text
                script_text = None
                m = re.search(
                    r"(\{\s*\"script\"\s*:\s*\".*\"\s*\})", content, re.DOTALL
                )
                if m:
                    try:
                        parsed = json.loads(m.group(1))
                        script_text = parsed.get("script")
                    except Exception:
                        script_text = None

                if not script_text:
                    # Use the raw content as a last resort
                    script_text = content

                # Post-process common issues: remove hedging intros and author lines
                # Sanitize final fallback script
                script_text = _sanitize_script(script_text)

                return script_text.strip()

        except httpx.HTTPError as e:
            raise Exception(f"LLM API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling LLM: {str(e)}")

    async def generate_topic_script(self, topic_name: str, papers: List[dict]) -> Any:
        """
        Generate a TTS script for multiple papers on the same topic.
        Includes intro, segues between papers, and conclusion.

        Args:
            topic_name: The name of the topic
            papers: List of dicts with 'title', 'filename', 'text'
        """

        # Build the prompt for the LLM
        # Build joined papers content if needed (not used directly below but kept for possible future prompts)
        # papers_content = "\n\n---PAPER SEPARATOR---\n\n".join(
        #     [
        #         f"TITLE: {paper['title']}\n\nCONTENT:\n{paper['text']}"
        #         for paper in papers
        #     ]
        # )

        # Load podcast prompt from file and use it as system instruction to improve adherence
        from pathlib import Path

        prompts_dir = Path(__file__).parent.parent / "prompts"
        prompt_path = prompts_dir / "podcast_dialog.md"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                podcast_instructions = f.read()
            # Strip code fences if present
            podcast_instructions = re.sub(r"^```[^\n]*\n", "", podcast_instructions)
            podcast_instructions = re.sub(r"\n```\s*$", "", podcast_instructions)
        except Exception:
            podcast_instructions = "You will create a short conversational podcast-style dialog between two speakers about the paper."

        # Build user prompt containing the papers' titles and content
        papers_text = "\n\n".join(
            [f"TITLE: {p['title']}\nCONTENT:\n{p['text']}" for p in papers]
        )

        user_prompt = f"Create a podcast dialog about: {topic_name}\n\nHere are the papers:\n\n{papers_text}\n\nReturn exactly one JSON object with key 'dialog' as described in the system instructions."

        # Call LLM with system message
        raw = await self.call_llm(
            user_prompt, system=podcast_instructions, temperature=0.0, max_tokens=2500
        )

        # Expect JSON {"dialog": [...]}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "dialog" in parsed:
                cleaned = {"dialog": []}
                for turn in parsed.get("dialog", []):
                    text = turn.get("text", "")
                    # Remove hedging phrases
                    text = re.sub(
                        r"(?i)\\b(appears to be|appears|seems to be|seems|may be|might be|may|might)\\b",
                        "",
                        text,
                    )
                    # Collapse authors lists to lead author
                    text = re.sub(
                        r"(?im)^\\s*authors?:\\s*(.+)$",
                        lambda m: "The lead author is "
                        + m.group(1).split(",")[0].strip(),
                        text,
                    )
                    m = re.search(
                        r"(?i)\\bby\\s+([^.\\n,]+?)(?:[,;]|\\sand\\b|\\s&\\s)", text
                    )
                    if m:
                        first = m.group(1).strip()
                        text = re.sub(
                            r"(?i)\\bby\\s+[^.\\n]+", "by " + first, text, count=1
                        )
                    cleaned["dialog"].append(
                        {"speaker": turn.get("speaker"), "text": text.strip()}
                    )
                return cleaned
        except Exception:
            pass

        # Fallback: return raw text if JSON parsing failed
        return raw

    async def generate_title(self, paper_text: str) -> str:
        """Generate a concise, publication-style title for the given paper text.

        Returns the title string or raises an Exception on error.
        """
        prompt = f"""Provide a concise, publication-quality title (no more than 12 words) for the following academic paper. Return only the title on a single line.

Paper text:
{paper_text}
"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {"Content-Type": "application/json"}

                if self.api_key:
                    headers["Ocp-Apim-Subscription-Key"] = self.api_key

                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )

                response.raise_for_status()
                result = response.json()
                content = (
                    result.get("choices", [{}])[0].get("message", {}).get("content", "")
                )

                # Keep only the first non-empty line
                for line in content.splitlines():
                    s = line.strip()
                    if s:
                        return s

                return content.strip()

        except httpx.HTTPError as e:
            raise Exception(f"LLM API error (generate_title): {str(e)}")
        except Exception as e:
            raise Exception(f"Error generating title: {str(e)}")
