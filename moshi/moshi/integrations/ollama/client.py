"""
Mimir - Ollama Client Integration
Interfaccia per comunicare con Ollama LLM (llama3.2:3b)
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, List, Optional, Any
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Configurazione Ollama"""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    temperature: float = 0.75
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.15
    num_ctx: int = 8192
    timeout: int = 120
    stream: bool = True


class OllamaClient:
    """Client per comunicare con Ollama via API REST"""
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self._conversation_history: List[Dict[str, str]] = []
        
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Genera risposta da Ollama con streaming
        
        Args:
            prompt: Testo input utente
            system_prompt: System prompt per personalità
            stream: Se True, ritorna token streaming
            **kwargs: Parametri aggiuntivi per generazione
            
        Yields:
            Token generati uno alla volta (se stream=True)
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with OllamaClient()' context manager")
        
        # Prepara payload
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "top_k": kwargs.get("top_k", self.config.top_k),
                "repeat_penalty": kwargs.get("repeat_penalty", self.config.repeat_penalty),
                "num_ctx": kwargs.get("num_ctx", self.config.num_ctx),
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        # Chiamata API
        url = f"{self.config.base_url}/api/generate"
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Ollama API error: {response.status} - {error_text}")
                
                if stream:
                    # Streaming response
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON from Ollama: {line}")
                                continue
                else:
                    # Non-streaming response
                    data = await response.json()
                    yield data.get("response", "")
                    
        except asyncio.TimeoutError:
            logger.error("Ollama request timeout")
            raise
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise
    
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        reset_history: bool = False,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Chat con memoria conversazione
        
        Args:
            message: Messaggio utente
            system_prompt: System prompt (usato solo al primo messaggio)
            reset_history: Se True, cancella storia conversazione
            stream: Streaming output
            **kwargs: Parametri generazione
            
        Yields:
            Token risposta
        """
        if reset_history:
            self._conversation_history.clear()
        
        # Aggiungi messaggio utente
        self._conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Costruisci prompt con storia
        if system_prompt and not self._conversation_history[:-1]:
            # Primo messaggio: include system prompt
            full_prompt = f"{system_prompt}\n\nUser: {message}\nAssistant:"
        else:
            # Costruisci da storia
            prompt_parts = []
            for msg in self._conversation_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}")
            prompt_parts.append("Assistant:")
            full_prompt = "\n".join(prompt_parts)
        
        # Genera risposta
        response_text = ""
        async for token in self.generate(full_prompt, stream=stream, **kwargs):
            response_text += token
            yield token
        
        # Salva risposta in storia
        self._conversation_history.append({
            "role": "assistant",
            "content": response_text.strip()
        })
    
    def clear_history(self):
        """Cancella storia conversazione"""
        self._conversation_history.clear()
    
    def get_history(self) -> List[Dict[str, str]]:
        """Ritorna storia conversazione"""
        return self._conversation_history.copy()
    
    async def check_health(self) -> bool:
        """Verifica se Ollama è raggiungibile"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            url = f"{self.config.base_url}/api/tags"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """Lista modelli disponibili"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            url = f"{self.config.base_url}/api/tags"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return [model["name"] for model in data.get("models", [])]
                return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []


# ========================================
# UTILITY FUNCTIONS
# ========================================

async def test_ollama_connection(
    base_url: str = "http://localhost:11434",
    model: str = "llama3.2:3b"
) -> bool:
    """
    Test rapido connessione Ollama
    
    Returns:
        True se connessione OK
    """
    config = OllamaConfig(base_url=base_url, model=model)
    async with OllamaClient(config) as client:
        if not await client.check_health():
            logger.error("Ollama non raggiungibile")
            return False
        
        models = await client.list_models()
        if model not in models:
            logger.error(f"Modello {model} non trovato. Disponibili: {models}")
            return False
        
        logger.info(f"✅ Ollama OK - Modello: {model}")
        return True


async def quick_test():
    """Test veloce client"""
    config = OllamaConfig(model="llama3.2:3b")
    
    async with OllamaClient(config) as client:
        print("Testing Ollama client...")
        
        # Health check
        if not await client.check_health():
            print("❌ Ollama non disponibile")
            return
        
        print("✅ Ollama connesso")
        
        # Test generazione
        print("\nGenerazione test:")
        prompt = "Ciao, immedesimati in Mimir, l'uomo più sapiente del mondo. Presentati brevemente."
        
        async for token in client.generate(prompt, stream=True):
            print(token, end="", flush=True)
        print("\n")


if __name__ == "__main__":
    # Test standalone
    asyncio.run(quick_test())
