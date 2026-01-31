from zipfile import Path
import httpx, json, re
import os
from typing import Optional, List


class LLMService:
    """Service for interacting with Ollama LLM"""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL")
        self.api_key = os.getenv("OLLAMA_API_KEY")
        self.model = os.getenv("OLLAMA_MODEL")

        if not all([self.base_url, self.model]):
            raise ValueError("OLLAMA_BASE_URL and OLLAMA_MODEL must be set")

    async def summarise_paper(self, paper_text: str) -> dict:
        """Generate a summary of an academic paper"""

        prompt = f"""Please analyze this academic paper and provide:
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
                        "messages": [{"role": "user", "content": prompt}],
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

    async def generate_text_to_speech_script(self, paper_text: str) -> str:
        """Generate an optimized text-to-speech script from a research paper."""
        from pathlib import Path

        # Load the TTS prompt from the markdown file
        prompt_path = Path(__file__).parent.parent / "prompts" / "tts_prompt.md"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                tts_instructions = f.read()
        except FileNotFoundError:
            raise Exception(f"TTS prompt file not found at {prompt_path}")
        except Exception as e:
            raise Exception(f"Error reading TTS prompt file: {str(e)}")

        prompt = f"""{tts_instructions}

---

{paper_text}"""

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
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )

                response.raise_for_status()
                result = response.json()

                # OpenAI-compatible API response
                content = (
                    result.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                return content

        except httpx.HTTPError as e:
            raise Exception(f"LLM API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling LLM: {str(e)}")

    async def generate_topic_script(self, topic_name: str, papers: List[dict]) -> str:
        """
        Generate a TTS script for multiple papers on the same topic.
        Includes intro, segues between papers, and conclusion.

        Args:
            topic_name: The name of the topic
            papers: List of dicts with 'title', 'filename', 'text'
        """

        # Build the prompt for the LLM
        papers_content = "\n\n---PAPER SEPARATOR---\n\n".join(
            [
                f"TITLE: {paper['title']}\n\nCONTENT:\n{paper['text']}"
                for paper in papers
            ]
        )

        prompt = f"""You are creating an audio podcast episode about: {topic_name}

    You have {len(papers)} research papers to summarize. Create a cohesive audio script that:

    1. Starts with a brief introduction to the topic ({topic_name})
    2. For each paper:
    - Introduce the paper's title and main research question
    - Summarize the key findings and methodology
    - Use natural segues between papers that highlight connections or contrasts
    3. End with a brief conclusion synthesizing the main themes

    Make it conversational and engaging for audio listening. Skip citations, author lists, and technical details that don't work well in audio.

    Here are the papers:

    {papers_content}

    Generate the complete audio script now:"""

        # Call your LLM (adjust based on your implementation)
        response = await self.call_llm(prompt)

        return response

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
