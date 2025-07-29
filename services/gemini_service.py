import httpx
import os
import json
import asyncio
import base64
from config.settings import GEMINI_API_KEY
from prompts.base_prompts import Prompts

class GeminiService:
    def __init__(self):
        # Switch to Google AI (Generative Language) API endpoint
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.api_key = GEMINI_API_KEY
        self.model_name = "gemini-2.5-flash"
        self.chat_sessions = {}

    def _get_chat_session(self, user_id: int):
        if user_id not in self.chat_sessions:
            self.chat_sessions[user_id] = []
        return self.chat_sessions[user_id]

    def reset_chat_session(self, user_id: int):
        if user_id in self.chat_sessions:
            del self.chat_sessions[user_id]

    async def _send_request(self, endpoint: str, json_data: dict, retries: int = 3, delay: int = 2) -> httpx.Response:
        url = f"{self.base_url}/{endpoint}?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        last_exception = None
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=json_data, headers=headers, timeout=None)
                    response.raise_for_status()
                    return response
            except httpx.ReadError as e:
                last_exception = e
                print(f"Attempt {attempt + 1}/{retries} failed with ReadError. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        
        raise last_exception

    async def generate_text_response(self, user_id: int, text: str) -> str:
        try:
            history = self._get_chat_session(user_id)
            history.append({"role": "user", "parts": [{"text": text}]})

            json_data = {
                "contents": history,
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            }

            endpoint = f"{self.model_name}:streamGenerateContent"
            response_stream = await self._send_request(endpoint, json_data)

            full_response_text = ""
            async for chunk in response_stream.aiter_bytes():
                try:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        chunk_str = chunk_str[6:]
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

            history.append({"role": "model", "parts": [{"text": full_response_text}]})
            return full_response_text
        except httpx.ReadError:
            return "Не удалось получить ответ от Gemini API после нескольких попыток. Проверьте сетевое соединение."
        except httpx.HTTPStatusError as e:
            await e.response.aread()
            return f"Произошла HTTP ошибка при обращении к Gemini API: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Произошла ошибка при обращении к Gemini API: {e}"

    async def generate_response_with_image(self, user_id: int, text: str, image_data: bytes) -> str:
        try:
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            contents = [
                {"role": "user", "parts": [
                    {"text": Prompts.IMAGE_UNDERSTANDING_PROMPT + "\n\n" + text},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
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

            endpoint = f"{self.model_name}:streamGenerateContent"
            response_stream = await self._send_request(endpoint, json_data)

            full_response_text = ""
            async for chunk in response_stream.aiter_bytes():
                try:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        chunk_str = chunk_str[6:]
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
        except httpx.ReadError:
            return "Не удалось получить ответ от Gemini API после нескольких попыток. Проверьте сетевое соединение."
        except httpx.HTTPStatusError as e:
            await e.response.aread()
            return f"Произошла HTTP ошибка при обращении к Gemini API: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Произошла ошибка при обращении к Gemini API: {e}"

    # ... (The rest of the methods remain the same, as they call the main text generation method) ...
    async def generate_response_with_audio(self, user_id: int, text: str, audio_data: bytes) -> str:
        prompt = Prompts.AUDIO_UNDERSTANDING_PROMPT + "\n\n" + text
        return await self.generate_text_response(user_id, prompt)

    async def delete_chat_history(self, user_id: int):
        self.reset_chat_session(user_id)
        return "Chat history has been cleared."
