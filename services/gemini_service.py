import httpx
import os
import json
import asyncio
import tempfile
from config.settings import GEMINI_API_KEY, GOOGLE_PROJECT_ID
from prompts.base_prompts import Prompts

class GeminiService:
    def __init__(self):
        # Use Vertex AI endpoint
        self.base_url = f"https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{GOOGLE_PROJECT_ID}/locations/us-central1/publishers/google/models"
        self.api_key = GEMINI_API_KEY
        self.model_name = "gemini-2.5-flash" # Or gemini-pro, depending on your needs
        self.chat_sessions = {}

    def _get_chat_session(self, user_id: int):
        if user_id not in self.chat_sessions:
            self.chat_sessions[user_id] = [] # History for this user
        return self.chat_sessions[user_id]

    def reset_chat_session(self, user_id: int):
        if user_id in self.chat_sessions:
            del self.chat_sessions[user_id]

    async def _send_request(self, endpoint: str, method: str = "POST", json_data: dict = None, files: dict = None, stream: bool = False) -> httpx.Response:
        headers = {"Content-Type": "application/json"}
        # For Vertex AI, API key is passed as Authorization header
        headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Construct URL for Vertex AI
        # Example: https://us-central1-aiplatform.googleapis.com/v1beta1/projects/PROJECT_ID/locations/us-central1/publishers/google/models/MODEL_ID:streamGenerateContent
        url = f"{self.base_url}/{endpoint}"

        async with httpx.AsyncClient() as client: 
            if method == "POST":
                if stream:
                    request = client.build_request(method, url, json=json_data, headers=headers, timeout=None)
                    response = await client.send(request, stream=True)
                    response.raise_for_status()
                    return response
                else:
                    response = await client.post(url, json=json_data, headers=headers, files=files, timeout=None)
            elif method == "GET":
                response = await client.get(url, headers=headers, timeout=None)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, timeout=None)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response

    async def generate_text_response(self, user_id: int, text: str) -> str:
        try:
            history = self._get_chat_session(user_id)
            
            # Add user's message to history
            history.append({"role": "user", "parts": [{"text": text}]})

            contents = []
            for msg in history:
                contents.append(msg)

            json_data = {
                "contents": contents,
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            }

            response_stream = await self._send_request(
                f"{self.model_name}:streamGenerateContent", # Endpoint is now just model_name:method
                json_data=json_data,
                stream=True
            )

            full_response_text = ""
            async for chunk in response_stream.aiter_bytes():
                try:
                    chunk_str = chunk.decode('utf-8')
                    # Vertex AI streaming response format is different, it's not 'data: ' prefixed
                    # It's just JSON objects separated by newlines
                    for line in chunk_str.splitlines():
                        if line.strip(): # Ensure line is not empty
                            data = json.loads(line)
                            if "candidates" in data and data["candidates"]:
                                for part in data["candidates"][0]["content"]["parts"]:
                                    if "text" in part:
                                        full_response_text += part["text"]
                except json.JSONDecodeError:
                    # Handle incomplete JSON chunks
                    pass
                except Exception as e:
                    print(f"Error processing chunk: {e}")

            # Add model's response to history
            history.append({"role": "model", "parts": [{"text": full_response_text}]})

            return full_response_text
        except httpx.HTTPStatusError as e:
            # Read the response content before accessing .text
            await e.response.aread()
            return f"Произошла HTTP ошибка при обращении к Gemini API: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Произошла ошибка при обращении к Gemini API: {e}"

    async def generate_response_with_image(self, user_id: int, text: str, image_data: bytes) -> str:
        try:
            # Vertex AI does not use Gemini Files API directly for image upload with generateContent
            # Instead, image data is sent directly in the request body.
            # This means we don't need temp files or separate upload/delete calls.

            contents = [
                {"role": "user", "parts": [
                    {"text": Prompts.IMAGE_UNDERSTANDING_PROMPT + "\n\n" + text},
                    {"inlineData": {"mimeType": "image/jpeg", "data": image_data.decode('latin-1')}} # Base64 encode if needed, but httpx might handle bytes directly
                ]}
            ]

            json_data = {
                "contents": contents,
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            }

            response_stream = await self._send_request(
                f"{self.model_name}:streamGenerateContent",
                json_data=json_data,
                stream=True
            )

            full_response_text = ""
            async for chunk in response_stream.aiter_bytes():
                try:
                    chunk_str = chunk.decode('utf-8')
                    for line in chunk_str.splitlines():
                        if line.strip():
                            data = json.loads(line)
                            if "candidates" in data and data["candidates"]:
                                for part in data["candidates"][0]["content"]["parts"]:
                                    if "text" in part:
                                        full_response_text += part["text"]
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"Error processing chunk: {e}")
            
            return full_response_text
        except httpx.HTTPStatusError as e:
            await e.response.aread()
            return f"Произошла HTTP ошибка при обращении к Gemini API: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Произошла ошибка при обращении к Gemini API: {e}"

    async def generate_response_with_audio(self, user_id: int, text: str, audio_data: bytes) -> str:
        # As per discussion, we avoid external tools like FFmpeg.
        # Gemini API does not directly support Speech-to-Text.
        # We will only process the text (caption) provided with the audio.
        prompt = Prompts.AUDIO_UNDERSTANDING_PROMPT + "\n\n" + text
        return await self.generate_text_response(user_id, prompt)

    async def generate_structured_output(self, user_id: int, prompt_text: str, schema: dict) -> str:
        full_prompt = Prompts.STRUCTURED_OUTPUT_PROMPT.format(fields=list(schema.keys())) + "\n\n" + prompt_text
        return await self.generate_text_response(user_id, full_prompt)

    async def perform_function_calling(self, user_id: int, prompt_text: str, tools: list) -> str:
        full_prompt = Prompts.FUNCTION_CALLING_PROMPT + "\n\n" + prompt_text
        return await self.generate_text_response(user_id, full_prompt)

    async def analyze_document(self, user_id: int, document_data: bytes, prompt_text: str) -> str:
        full_prompt = Prompts.DOCUMENT_PROCESSING_PROMPT + "\n\n" + prompt_text
        return await self.generate_text_response(user_id, full_prompt)

    async def analyze_video(self, user_id: int, video_data: bytes, prompt_text: str) -> str:
        full_prompt = Prompts.VIDEO_UNDERSTANDING_PROMPT + "\n\n" + prompt_text
        return await self.generate_text_response(user_id, full_prompt)

    async def execute_code(self, user_id: int, code: str, prompt_text: str) -> str:
        full_prompt = Prompts.CODE_EXECUTION_PROMPT + "\n\n" + prompt_text + "\n\nCode to execute:\n" + code
        return await self.generate_text_response(user_id, full_prompt)

    async def analyze_url_context(self, user_id: int, url: str, prompt_text: str) -> str:
        full_prompt = Prompts.URL_CONTEXT_PROMPT + "\n\n" + prompt_text + "\n\nURL: " + url
        return await self.generate_text_response(user_id, full_prompt)

    async def perform_google_search(self, user_id: int, query: str, prompt_text: str) -> str:
        full_prompt = Prompts.GOOGLE_SEARCH_PROMPT + "\n\n" + prompt_text + "\n\nSearch query: " + query
        return await self.generate_text_response(user_id, full_prompt)

    async def handle_long_context(self, user_id: int, text: str) -> str:
        full_prompt = Prompts.LONG_CONTEXT_PROMPT + "\n\n" + text
        return await self.generate_text_response(user_id, full_prompt)