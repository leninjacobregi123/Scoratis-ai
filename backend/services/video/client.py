import os
import httpx
import logging
import asyncio
import concurrent.futures
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class OllamaVideoClient:
    def __init__(self):
        self._use_api = False
        self._initialize()

    def _initialize(self):
        try:
            from llm_service import llm_service
            config = llm_service.get_current_config()
            if config and config.get("provider") not in ["ollama", "lmstudio", "localai", "textgenwebui"]:
                if llm_service.current_config and llm_service.current_config.api_key_encrypted:
                    self._use_api = True
                    self._llm_service = llm_service
            if not self._use_api:
                self._ollama_client = OllamaVideoClient()
        except Exception:
            self._ollama_client = OllamaVideoClient()

    def generate(self, prompt: str, **kwargs) -> str:
        if self._use_api:
            async def _run():
                return await self._llm_service.generate(messages=[{"role":"user","content":prompt}])
            try:
                loop = asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, _run()).result(timeout=120)
            except RuntimeError:
                return asyncio.run(_run())
        return self._ollama_client.generate(prompt, **kwargs)

class SmartManimClient:
