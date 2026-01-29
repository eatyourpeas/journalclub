from zipfile import Path
import httpx
import os
from typing import Optional


class LLMService:
    """Service for interacting with Ollama LLM"""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL")
        self.api_key = os.getenv("OLLAMA_API_KEY")
        self.model = os.getenv("OLLAMA_MODEL")

        if not all([self.base_url, self.model]):
            raise ValueError("OLLAMA_BASE_URL and OLLAMA_MODEL must be set")

    async def summarise_paper(self, paper_text: str) -> dict:
        """
        Generate a summary of an academic paper

        Args:
            paper_text: Full text of the paper

        Returns:
            Dictionary with summary and key points
        """
        prompt = f"""Please analyze this academic paper and provide:
1. A concise summary (2-3 paragraphs)
2. Key findings and contributions (as bullet points)
3. Methodology used
4. Main conclusions

Paper text:
{paper_text}

Please structure your response as JSON with keys: summary, key_points, methodology, conclusions"""

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

                # Extract the response content
                # OpenAI-compatible API returns: {"choices": [{"message": {"content": "..."}}]}
                content = (
                    result.get("choices", [{}])[0].get("message", {}).get("content", "")
                )

                return {"raw_response": content, "model_used": self.model}

        except httpx.HTTPError as e:
            raise Exception(f"LLM API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling LLM: {str(e)}")

    async def summarise_paper_stream(self, paper_text: str):
        """
        Generate a summary of an academic paper with streaming response

        Args:
            paper_text: Full text of the paper

        Yields:
            Server-sent events with streaming content
        """
        prompt = f"""Please analyze this academic paper and provide:
1. A concise summary (2-3 paragraphs)
2. Key findings and contributions (as bullet points)
3. Methodology used
4. Main conclusions

Paper text:
{paper_text}

Please structure your response as JSON with keys: summary, key_points, methodology, conclusions"""

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                headers = {"Content-Type": "application/json"}

                if self.api_key:
                    headers["Ocp-Apim-Subscription-Key"] = self.api_key

                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix

                            if data == "[DONE]":
                                break

                            try:
                                import json

                                chunk = json.loads(data)
                                content = (
                                    chunk.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content", "")
                                )

                                if content:
                                    yield f"data: {json.dumps({'content': content})}"

                            except json.JSONDecodeError:
                                continue

        except httpx.HTTPError as e:
            yield f"data: {json.dumps({'error': f'LLM API error: {str(e)}'})}"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Error calling LLM: {str(e)}'})}"

    async def generate_text_to_speech_script(self, paper_text: str) -> str:
        """
            Generate an optimized text-to-speech script from a research paper.

            This method instructs the LLM to:
            - Start with an introduction using the abstract
            - Skip keywords, author lists, affiliations
            - Skip the abstract section when reading the main body
            - Remove in-text citations like [1], (Author et al., 2023)
            - Skip figures, tables, and equations
            - Make content flow naturally for listening

        Args:
            paper_text: Full text of the paper

        Returns:
            Formatted script for TTS
        """
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
        prompt = f""""{tts_instructions}

---

{paper_text}

Generate the TTS script now:"""

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
