import google.generativeai as genai
from config.settings import GEMINI_API_KEY
from prompts.base_prompts import Prompts
import asyncio
import tempfile
import os

genai.configure(api_key=GEMINI_API_KEY)

class GeminiService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.chat_sessions = {}

    def _get_chat_session(self, user_id: int):
        if user_id not in self.chat_sessions:
            self.chat_sessions[user_id] = self.model.start_chat(history=[])
        return self.chat_sessions[user_id]

    def reset_chat_session(self, user_id: int):
        if user_id in self.chat_sessions:
            del self.chat_sessions[user_id]

    async def generate_text_response(self, user_id: int, text: str) -> str:
        try:
            chat = self._get_chat_session(user_id)
            prompt = Prompts.TEXT_GENERATION_PROMPT + "\n\n" + text
            response = await chat.send_message_async(prompt, stream=True)
            full_response = []
            async for chunk in response:
                full_response.append(chunk.text)
            return "".join(full_response)
        except Exception as e:
            return f"Произошла ошибка при обращении к Gemini API: {e}"

    async def generate_response_with_image(self, user_id: int, text: str, image_data: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name
            
            # Upload image to Gemini Files API
            gemini_file_resource = await asyncio.to_thread(
                genai.upload_file,
                path=temp_file_path,
                display_name=f"user_image_{user_id}.jpg",
                mime_type="image/jpeg"
            )
            
            chat = self._get_chat_session(user_id)
            prompt = Prompts.IMAGE_UNDERSTANDING_PROMPT + "\n\n" + text
            
            # Send prompt and image to Gemini
            contents_for_gemini = [
                prompt,
                gemini_file_resource
            ]
            response = await chat.send_message_async(contents_for_gemini, stream=True)
            
            full_response = []
            async for chunk in response:
                full_response.append(chunk.text)
            
            # Delete temporary file and uploaded file from Gemini Files API
            os.remove(temp_file_path)
            await asyncio.to_thread(genai.delete_file, gemini_file_resource.name)
            
            return "".join(full_response)
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
