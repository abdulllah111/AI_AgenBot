import httpx
import os
import json
import asyncio
import tempfile
from config.settings import GEMINI_API_KEY, HTTP_PROXY_URL
from prompts.base_prompts import Prompts

class GeminiService:
    def __init__(self):
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.api_key = GEMINI_API_KEY
        self.model_name = "gemini-1.5-flash"
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
        url = f"{self.base_url}/{endpoint}?key={self.api_key}"

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
                f"models/{self.model_name}:streamGenerateContent",
                json_data=json_data,
                stream=True
            )

            full_response_text = ""
            async for chunk in response_stream.aiter_bytes():
                try:
                    # Each chunk might contain multiple JSON objects or partial JSON
                    # Need to parse carefully. This is a simplified parsing.
                    chunk_str = chunk.decode('utf-8')
                    # Remove 'data: ' prefix and parse each line as JSON
                    for line in chunk_str.splitlines():
                        if line.startswith("data: "):
                            json_part = line[len("data: "):]
                            data = json.loads(json_part)
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
            # 1. Upload image to Gemini Files API
            # Create a temporary file to write image data
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name
            
            # Prepare file for upload
            files = {'file': (os.path.basename(temp_file_path), open(temp_file_path, 'rb'), 'image/jpeg')}
            
            upload_response = await self._send_request(
                "files",
                method="POST",
                files=files
            )
            upload_response_json = upload_response.json()
            file_resource_name = upload_response_json["name"]
            
            # 2. Wait for file to be processed (optional, but good practice)
            # In a real app, you might poll the file status
            await asyncio.sleep(2) # Give Gemini some time to process

            # 3. Send prompt and image reference to Gemini model
            contents = [
                {"role": "user", "parts": [
                    {"text": Prompts.IMAGE_UNDERSTANDING_PROMPT + "\n\n" + text},
                    {"fileData": {"mimeType": "image/jpeg", "uri": f"gemini-cloud-file://{file_resource_name}"}}
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
                f"models/{self.model_name}:streamGenerateContent",
                json_data=json_data,
                stream=True
            )

            full_response_text = ""
            async for chunk in response_stream.aiter_bytes():
                try:
                    chunk_str = chunk.decode('utf-8')
                    for line in chunk_str.splitlines():
                        if line.startswith("data: "):
                            json_part = line[len("data: "):]
                            data = json.loads(json_part)
                            if "candidates" in data and data["candidates"]:
                                for part in data["candidates"][0]["content"]["parts"]:
                                    if "text" in part:
                                        full_response_text += part["text"]
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"Error processing chunk: {e}")

            # 4. Delete temporary file and uploaded file from Gemini Files API
            os.remove(temp_file_path)
            await self._send_request(f"files/{file_resource_name}", method="DELETE")
            
            return full_response_text
        except httpx.HTTPStatusError as e:
            # Read the response content before accessing .text
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
        # This is a placeholder. Actual implementation would involve specific prompt engineering
        # and potentially parsing the model's output to ensure it matches the schema.
        full_prompt = Prompts.STRUCTURED_OUTPUT_PROMPT.format(fields=list(schema.keys())) + "\n\n" + prompt_text
        return await self.generate_text_response(user_id, full_prompt)

    async def perform_function_calling(self, user_id: int, prompt_text: str, tools: list) -> str:
        # This is a placeholder. Actual implementation would involve defining tools
        # and letting the model decide which tool to call based on the prompt.
        full_prompt = Prompts.FUNCTION_CALLING_PROMPT + "\n\n" + prompt_text
        return await self.generate_text_response(user_id, full_prompt)

    async def analyze_document(self, user_id: int, document_data: bytes, prompt_text: str) -> str:
        # This is a placeholder. Requires a separate OCR/document parsing library to extract text
        # from document_data, then send the extracted text to Gemini.
        full_prompt = Prompts.DOCUMENT_PROCESSING_PROMPT + "\n\n" + prompt_text
        return await self.generate_text_response(user_id, full_prompt)

    async def analyze_video(self, user_id: int, video_data: bytes, prompt_text: str) -> str:
        # This is a placeholder. Video understanding is complex and might involve frame extraction
        # and sending multiple image parts to Gemini, or using a specialized video model.
        full_prompt = Prompts.VIDEO_UNDERSTANDING_PROMPT + "\n\n" + prompt_text
        return await self.generate_text_response(user_id, full_prompt)

    async def execute_code(self, user_id: int, code: str, prompt_text: str) -> str:
        # This is a placeholder. Code execution would typically be a tool called by Function Calling.
        full_prompt = Prompts.CODE_EXECUTION_PROMPT + "\n\n" + prompt_text + "\n\nCode to execute:\n" + code
        return await self.generate_text_response(user_id, full_prompt)

    async def analyze_url_context(self, user_id: int, url: str, prompt_text: str) -> str:
        # This is a placeholder. Requires a web scraping/fetching library to get content from URL.
        full_prompt = Prompts.URL_CONTEXT_PROMPT + "\n\n" + prompt_text + "\n\nURL: " + url
        return await self.generate_text_response(user_id, full_prompt)

    async def perform_google_search(self, user_id: int, query: str, prompt_text: str) -> str:
        # This is a placeholder. Requires integration with a search API (e.g., Google Custom Search).
        full_prompt = Prompts.GOOGLE_SEARCH_PROMPT + "\n\n" + prompt_text + "\n\nSearch query: " + query
        return await self.generate_text_response(user_id, full_prompt)

    async def handle_long_context(self, user_id: int, text: str) -> str:
        # Long context is handled internally by the model. This method is just for demonstration.
        full_prompt = Prompts.LONG_CONTEXT_PROMPT + "\n\n" + text
        return await self.generate_text_response(user_id, full_prompt)