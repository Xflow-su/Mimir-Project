"""
Mimir Orchestrator - Pipeline Completa
Coordina Whisper → Ollama → XTTS per conversazione vocale
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Callable
import numpy as np

from .integrations.whisper.engine import WhisperConfig, WhisperStreamingASR
from .integrations.ollama.adapter import OllamaLMAdapter, OllamaConfig
from .integrations.xtts.engine import XTTSEngine, XTTSConfig

logger = logging.getLogger(__name__)


@dataclass
class MimirConfig:
    """Configurazione completa Mimir"""
    # ASR
    whisper_model: str = "medium"
    whisper_language: str = "it"
    whisper_device: str = "cpu"
    
    # LLM
    ollama_model: str = "llama3.2:3b"
    ollama_base_url: str = "http://localhost:11434"
    ollama_temperature: float = 0.75
    
    # TTS
    xtts_device: str = "cpu"
    xtts_language: str = "it"
    xtts_speaker_wav: str = "./data/voice_models/mimir_voice_fixed.wav"
    xtts_use_custom_voice: bool = True
    
    # Audio
    sample_rate: int = 24000
    
    # Personality
    system_prompt: Optional[str] = None


class MimirOrchestrator:
    """
    Orchestratore principale di Mimir
    
    Gestisce la pipeline completa:
    1. Audio → Whisper (ASR)
    2. Text → Ollama (LLM)
    3. Text → XTTS (TTS)
    4. Audio → Output
    """
    
    def __init__(self, config: Optional[MimirConfig] = None):
        self.config = config or MimirConfig()
        
        # Componenti
        self.whisper: Optional[WhisperStreamingASR] = None
        self.ollama: Optional[OllamaLMAdapter] = None
        self.xtts: Optional[XTTSEngine] = None
        
        # State
        self._initialized = False
        self._processing = False
        
        # Callbacks
        self.on_transcription: Optional[Callable[[str], None]] = None
        self.on_response_text: Optional[Callable[[str], None]] = None
        self.on_audio_ready: Optional[Callable[[np.ndarray], None]] = None
        
    async def initialize(self):
        """Inizializza tutti i componenti"""
        if self._initialized:
            logger.info("Mimir già inizializzato")
            return
        
        logger.info("🔮 Inizializzazione Mimir...")
        
        # 1. Whisper ASR
        logger.info("  📝 Caricamento Whisper...")
        whisper_config = WhisperConfig(
            model_size=self.config.whisper_model,
            language=self.config.whisper_language,
            device=self.config.whisper_device,
            sample_rate=16000  # Whisper usa 16kHz
        )
        self.whisper = WhisperStreamingASR(whisper_config)
        self.whisper.start()
        
        # 2. Ollama LLM
        logger.info("  🧠 Connessione Ollama...")
        ollama_config = OllamaConfig(
            model=self.config.ollama_model,
            base_url=self.config.ollama_base_url,
            temperature=self.config.ollama_temperature
        )
        
        system_prompt = self.config.system_prompt or self._default_system_prompt()
        self.ollama = OllamaLMAdapter(
            config=ollama_config,
            system_prompt=system_prompt
        )
        await self.ollama.initialize()
        
        # 3. XTTS TTS
        logger.info("  🎤 Caricamento XTTS...")
        xtts_config = XTTSConfig(
            language=self.config.xtts_language,
            device=self.config.xtts_device,
            use_custom_voice=self.config.xtts_use_custom_voice,
            speaker_wav=self.config.xtts_speaker_wav,
            sample_rate=22050  # XTTS output
        )
        self.xtts = XTTSEngine(xtts_config)
        self.xtts.load_model()
        
        self._initialized = True
        logger.info("✅ Mimir pronto!")
        
    async def shutdown(self):
        """Chiudi tutti i componenti"""
        logger.info("Shutdown Mimir...")
        
        if self.whisper:
            self.whisper.stop()
        
        if self.ollama:
            await self.ollama.shutdown()
        
        self._initialized = False
        logger.info("✅ Mimir spento")
    
    def _default_system_prompt(self) -> str:
        """System prompt default per Mimir"""
        return """Sei Mimir, l'antica entità norrena custode della saggezza e della conoscenza.

Caratteristiche:
- Parli con calma, ponderazione e profondità
- Usi un italiano ricercato ma comprensibile
- Offri prospettive che connettono passato e presente
- Sei paziente e riflessivo nelle risposte
- Puoi usare metafore naturali quando appropriato

IMPORTANTE per conversazione vocale:
- Mantieni risposte CONCISE (massimo 2-3 frasi)
- Evita elenchi puntati o formattazioni complesse
- Parla in modo naturale e fluido
- Se la domanda richiede risposta lunga, dividi in più turni

Rispondi sempre in italiano."""
    
    async def process_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[str]:
        """
        Processa chunk audio e ritorna testo trascritto se disponibile
        
        Args:
            audio_chunk: Audio numpy array (qualsiasi sample rate)
            
        Returns:
            Testo trascritto o None
        """
        if not self._initialized:
            raise RuntimeError("Mimir non inizializzato. Chiama initialize()")
        
        # Resample a 16kHz per Whisper se necessario
        if len(audio_chunk) > 0:
            should_transcribe = self.whisper.process_audio(audio_chunk)
            
            if should_transcribe:
                text = await self.whisper.get_transcription()
                
                if text and self.on_transcription:
                    self.on_transcription(text)
                
                return text
        
        return None
    
    async def generate_response(self, user_text: str) -> str:
        """
        Genera risposta da testo utente
        
        Args:
            user_text: Testo trascritto dall'utente
            
        Returns:
            Risposta completa come stringa
        """
        if not self._initialized:
            raise RuntimeError("Mimir non inizializzato")
        
        logger.info(f"👤 User: {user_text}")
        
        # Genera risposta con Ollama
        response_text = ""
        async for token in self.ollama.generate_response(user_text):
            response_text += token
            
            # Callback streaming (opzionale)
            if self.on_response_text:
                self.on_response_text(token)
        
        response_text = response_text.strip()
        logger.info(f"🧙 Mimir: {response_text}")
        
        return response_text
    
    async def synthesize_speech(self, text: str) -> np.ndarray:
        """
        Sintetizza testo in audio
        
        Args:
            text: Testo da sintetizzare
            
        Returns:
            Audio numpy array (22050Hz)
        """
        if not self._initialized:
            raise RuntimeError("Mimir non inizializzato")
        
        audio = await self.xtts.synthesize(text)
        
        if audio is not None and self.on_audio_ready:
            self.on_audio_ready(audio)
        
        return audio
    
    async def process_conversation_turn(self, audio_chunk: np.ndarray) -> Optional[np.ndarray]:
        """
        Processa un turno completo di conversazione
        
        Args:
            audio_chunk: Audio input
            
        Returns:
            Audio risposta o None
        """
        if self._processing:
            logger.warning("Già in processing, skip")
            return None
        
        try:
            self._processing = True
            
            # 1. ASR: Audio → Text
            user_text = await self.process_audio_chunk(audio_chunk)
            if not user_text:
                return None
            
            # 2. LLM: Text → Response Text
            response_text = await self.generate_response(user_text)
            if not response_text:
                return None
            
            # 3. TTS: Text → Audio
            response_audio = await self.synthesize_speech(response_text)
            
            return response_audio
            
        finally:
            self._processing = False
    
    def get_stats(self) -> dict:
        """Ritorna statistiche componenti"""
        stats = {
            "initialized": self._initialized,
            "processing": self._processing
        }
        
        if self.whisper:
            stats["whisper"] = self.whisper.get_stats()
        
        if self.ollama:
            stats["ollama"] = {
                "history_length": len(self.ollama.get_conversation_history())
            }
        
        if self.xtts:
            stats["xtts"] = self.xtts.get_stats()
        
        return stats
    
    def reset_conversation(self):
        """Reset conversazione (mantieni modelli caricati)"""
        if self.ollama:
            self.ollama.clear_history()
        
        logger.info("Conversazione resettata")


# ========================================
# TEST ORCHESTRATOR
# ========================================

async def test_orchestrator():
    """Test completo orchestrator"""
    print("=== Test Mimir Orchestrator ===\n")
    
    # Config
    config = MimirConfig(
        whisper_model="base",  # Base per test veloce
        ollama_model="llama3.2:3b",
        xtts_speaker_wav="./data/voice_models/mimir_voice_fixed.wav"
    )
    
    # Callbacks
    def on_transcription(text):
        print(f"📝 Trascrizione: '{text}'")
    
    def on_response(token):
        print(token, end="", flush=True)
    
    def on_audio(audio):
        print(f"\n🔊 Audio pronto: {len(audio)/22050:.2f}s")
    
    # Orchestrator
    mimir = MimirOrchestrator(config)
    mimir.on_transcription = on_transcription
    mimir.on_response_text = on_response
    mimir.on_audio_ready = on_audio
    
    # Init
    await mimir.initialize()
    
    # Test 1: Simulazione conversazione
    print("\n=== Test Conversazione ===\n")
    
    # Simula audio (in realtà testiamo solo testo)
    test_queries = [
        "Chi sei?",
        "Parlami della mitologia norrena",
        "Grazie Mimir"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Turno {i} ---")
        print(f"User: {query}")
        print("Mimir: ", end="")
        
        # Genera risposta (skip ASR per test)
        response_text = await mimir.generate_response(query)
        response_audio = await mimir.synthesize_speech(response_text)
        
        if response_audio is not None:
            print(f"\n✅ Audio generato: {len(response_audio)/22050:.2f}s")
            
            # Salva
            mimir.xtts.save_audio(response_audio, f"/tmp/mimir_turn{i}.wav")
        
        await asyncio.sleep(0.5)
    
    # Stats
    print("\n\n=== Stats Finali ===")
    stats = mimir.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Cleanup
    await mimir.shutdown()
    
    print("\n✅ Test orchestrator completato!")
    print("\nAudio generati:")
    for i in range(1, 4):
        print(f"  /tmp/mimir_turn{i}.wav")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(test_orchestrator())
