"""
Mimir - Ollama Adapter
Adapter per rendere Ollama compatibile con l'interfaccia LMGen di Moshi
"""

import asyncio
import logging
from typing import Optional, AsyncIterator
import torch
import sentencepiece

from .client import OllamaClient, OllamaConfig

logger = logging.getLogger(__name__)


class OllamaLMAdapter:
    """
    Adapter che fa da bridge tra Ollama e l'interfaccia LMGen di Moshi
    
    Questa classe:
    - Prende input dall'audio pipeline di Moshi
    - Converte in testo via Whisper (gestito dal chiamante)
    - Passa a Ollama per generazione
    - Converte output testuale in formato compatibile per XTTS
    """
    
    def __init__(
        self,
        config: Optional[OllamaConfig] = None,
        text_tokenizer: Optional[sentencepiece.SentencePieceProcessor] = None,
        system_prompt: Optional[str] = None,
        device: str = "cpu"
    ):
        """
        Args:
            config: Configurazione Ollama
            text_tokenizer: Tokenizer testo (manteniamo compatibilità con Moshi)
            system_prompt: System prompt per personalità Mimir
            device: Device PyTorch (cpu/cuda)
        """
        self.config = config or OllamaConfig()
        self.text_tokenizer = text_tokenizer
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.device = device
        
        self.client: Optional[OllamaClient] = None
        self._initialized = False
        
    def _default_system_prompt(self) -> str:
        """System prompt default per Mimir"""
        return """Sei Mimir, l'antica entità norrena custode della saggezza e della conoscenza.

Caratteristiche:
- Parli con calma, ponderazione e profondità
- Usi un italiano ricercato ma comprensibile
- Offri prospettive che connettono passato e presente
- Sei paziente e riflessivo nelle risposte
- Puoi usare metafore naturali quando appropriato

Rispondi sempre in italiano. Mantieni le risposte concise ma significative (massimo 3-4 frasi per risposta in conversazione vocale)."""
    
    async def initialize(self):
        """Inizializza client Ollama"""
        if self._initialized:
            return
        
        self.client = OllamaClient(self.config)
        await self.client.__aenter__()
        
        # Verifica connessione
        if not await self.client.check_health():
            raise RuntimeError("Impossibile connettersi a Ollama. Assicurati che 'ollama serve' sia in esecuzione.")
        
        self._initialized = True
        logger.info(f"✅ OllamaLMAdapter inizializzato - Modello: {self.config.model}")
    
    async def shutdown(self):
        """Chiudi client"""
        if self.client:
            await self.client.__aexit__(None, None, None)
            self._initialized = False
    
    async def generate_response(
        self,
        user_text: str,
        reset_conversation: bool = False,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Genera risposta da testo utente
        
        Args:
            user_text: Testo trascritto dall'utente (da Whisper)
            reset_conversation: Reset storia conversazione
            **kwargs: Parametri aggiuntivi generazione
            
        Yields:
            Token di testo generati
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            async for token in self.client.chat(
                message=user_text,
                system_prompt=self.system_prompt,
                reset_history=reset_conversation,
                stream=True,
                **kwargs
            ):
                yield token
                
        except Exception as e:
            logger.error(f"Errore generazione Ollama: {e}")
            yield "Mi dispiace, ho avuto un problema nel generare la risposta."
    
    async def generate_response_complete(
        self,
        user_text: str,
        reset_conversation: bool = False,
        **kwargs
    ) -> str:
        """
        Genera risposta completa (non streaming)
        
        Args:
            user_text: Testo utente
            reset_conversation: Reset conversazione
            
        Returns:
            Risposta completa come stringa
        """
        response = ""
        async for token in self.generate_response(user_text, reset_conversation, **kwargs):
            response += token
        return response.strip()
    
    def clear_history(self):
        """Cancella storia conversazione"""
        if self.client:
            self.client.clear_history()
    
    def get_conversation_history(self):
        """Ottieni storia conversazione"""
        if self.client:
            return self.client.get_history()
        return []
    
    def update_system_prompt(self, new_prompt: str):
        """Aggiorna system prompt"""
        self.system_prompt = new_prompt
        logger.info("System prompt aggiornato")


class MimirLMGen:
    """
    Wrapper compatibile con LMGen di Moshi, ma usa Ollama dietro le quinte
    
    Questa classe mantiene l'interfaccia di Moshi ma delega a Ollama.
    Utile per minimizzare modifiche al server.py di Moshi.
    """
    
    def __init__(
        self,
        ollama_config: Optional[OllamaConfig] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        self.adapter = OllamaLMAdapter(
            config=ollama_config,
            system_prompt=system_prompt
        )
        self._current_response: Optional[str] = None
        
    async def initialize(self):
        """Init adapter"""
        await self.adapter.initialize()
    
    async def shutdown(self):
        """Shutdown adapter"""
        await self.adapter.shutdown()
    
    async def step(self, user_text: str) -> AsyncIterator[str]:
        """
        Step di generazione (compatibilità con interfaccia Moshi)
        
        Args:
            user_text: Testo utente
            
        Yields:
            Token generati
        """
        async for token in self.adapter.generate_response(user_text):
            yield token
    
    def streaming_forever(self, batch_size: int = 1):
        """Compatibilità con Moshi - no-op per noi"""
        pass
    
    def reset(self):
        """Reset stato generatore"""
        self.adapter.clear_history()


# ========================================
# TEST
# ========================================

async def test_adapter():
    """Test dell'adapter"""
    print("=== Test Ollama Adapter ===\n")
    
    config = OllamaConfig(model="llama3.2:3b")
    adapter = OllamaLMAdapter(config=config)
    
    try:
        await adapter.initialize()
        print("✅ Adapter inizializzato\n")
        
        # Test 1: Risposta singola
        print("Test 1: Generazione singola")
        print("User: Salve Mimir, chi sei?")
        print("Mimir: ", end="", flush=True)
        
        async for token in adapter.generate_response("Salve Mimir, chi sei?", reset_conversation=True):
            print(token, end="", flush=True)
        print("\n")
        
        # Test 2: Conversazione
        print("Test 2: Continuazione conversazione")
        print("User: Raccontami della mitologia norrena")
        print("Mimir: ", end="", flush=True)
        
        async for token in adapter.generate_response("Raccontami della mitologia norrena"):
            print(token, end="", flush=True)
        print("\n")
        
        # Storia
        print("Storia conversazione:")
        for msg in adapter.get_conversation_history():
            print(f"  {msg['role']}: {msg['content'][:60]}...")
        
    finally:
        await adapter.shutdown()
        print("\n✅ Test completato")


if __name__ == "__main__":
    asyncio.run(test_adapter())
