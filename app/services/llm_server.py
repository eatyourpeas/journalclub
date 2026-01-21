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
                headers = {
                    "Content-Type": "application/json"
                }
                
                if self.api_key:
                    headers["Ocp-Apim-Subscription-Key"] = self.api_key
                
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "stream": False
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract the response content
                # OpenAI-compatible API returns: {"choices": [{"message": {"content": "..."}}]}
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                return {
                    "raw_response": content,
                    "model_used": self.model
                }
        
        except httpx.HTTPError as e:
            raise Exception(f"LLM API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling LLM: {str(e)}")
    
    async def generate_text_to_speech_script(self, paper_text: str) -> str:
        """
        Generate a script suitable for text-to-speech reading
        
        Args:
            paper_text: Full text of the paper
            
        Returns:
            Formatted script for TTS
        """
        prompt = f"""Convert this academic paper into a clear, spoken script suitable for text-to-speech.
Remove citations, simplify complex sentences, and make it flow naturally for audio.
Keep the key information and findings intact.

Paper text:
{paper_text}"""

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                headers = {
                    "Content-Type": "application/json"
                }
                
                if self.api_key:
                    headers["Ocp-Apim-Subscription-Key"] = self.api_key
                
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "stream": False
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                # OpenAI-compatible API response
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content
        
        except httpx.HTTPError as e:
            raise Exception(f"LLM API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling LLM: {str(e)}")