"""
Mimir - Whisper Adapter
Adapter per integrare Whisper nel pipeline audio di Moshi
"""

import asyncio
import logging
from typing import Optional, Callable
import numpy as np
import torch

from .engine import WhisperEngine, WhisperConfig, WhisperStreamingASR

logger = logging.getLogger(__name__)


class WhisperMimiAdapter:
    """
    Adapter che converte audio da Mimi format a Whisper e viceversa
    
    Moshi usa Mimi codec che:
    - Sample rate: 24kHz
    - Output: codici audio compressi
    
    Whisper richiede:
    - Sample rate: 16kHz
    - Input: audio raw float32
    
    Questo adapter gestisce la conversione.
    """
    
    def __init__(
        self,
        config: Optional[WhisperConfig] = None,
        mimi_sample_rate: int = 24000,
        on_transcription: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            config: Config Whisper
            mimi_sample_rate: Sample rate Mimi (default 24kHz)
            on_transcription: Callback quando arriva trascrizione
        """
        self.config = config or WhisperConfig()
        self.mimi_sample_rate = mimi_sample_rate
        self.whisper_sample_rate = self.config.sample_rate
        self.on_transcription = on_transcription
        
        self.asr = WhisperStreamingASR(config)
        self._initialized = False
        
    def initialize(self):
        """Inizializza Whisper"""
        if self._initialized:
            return
        
        logger.info("Inizializzazione Whisper ASR...")
        self.asr.start()
        self._initialized = True
        logger.info("✅ Whisper ASR pronto")
    
    def shutdown(self):
        """Shutdown Whisper"""
        if self._initialized:
            self.asr.stop()
            self._initialized = False
    
    def resample_audio(self, audio: np.ndarray, from_sr: int, to_sr: int) -> np.ndarray:
        """
        Resample audio da from_sr a to_sr
        
        Args:
            audio: Audio array
            from_sr: Sample rate originale
            to_sr: Sample rate target
            
        Returns:
            Audio resampleato
        """
        if from_sr == to_sr:
            return audio
        
        # Resampling semplice (linear interpolation)
        # Per produzione: usare librosa.resample per qualità superiore
        duration = len(audio) / from_sr
        new_length = int(duration * to_sr)
        
        indices = np.linspace(0, len(audio) - 1, new_length)
        resampled = np.interp(indices, np.arange(len(audio)), audio)
        
        return resampled.astype(np.float32)
    
    async def process_mimi_audio(self, audio_24k: np.ndarray) -> Optional[str]:
        """
        Processa audio da Mimi (24kHz) e ritorna trascrizione se disponibile
        
        Args:
            audio_24k: Audio a 24kHz (da Mimi)
            
        Returns:
            Testo trascritto o None
        """
        if not self._initialized:
            raise RuntimeError("Adapter non inizializzato. Chiama initialize()")
        
        # Resample 24kHz → 16kHz
        audio_16k = self.resample_audio(
            audio_24k,
            from_sr=self.mimi_sample_rate,
            to_sr=self.whisper_sample_rate
        )
        
        # Processa con Whisper
        should_transcribe = self.asr.process_audio(audio_16k)
        
        if should_transcribe:
            text = await self.asr.get_transcription()
            
            if text and self.on_transcription:
                # Callback
                self.on_transcription(text)
            
            return text
        
        return None
    
    def decode_mimi_codes(self, codes: torch.Tensor, mimi_decoder) -> np.ndarray:
        """
        Decodifica codici Mimi in audio raw
        
        Args:
            codes: Tensor codici Mimi
            mimi_decoder: Decoder Mimi
            
        Returns:
            Audio numpy array 24kHz
        """
        with torch.no_grad():
            audio = mimi_decoder.decode(codes)
            
            # Converti a numpy
            if isinstance(audio, torch.Tensor):
                audio = audio.cpu().numpy()
            
            # Assicurati sia mono e 1D
            if audio.ndim > 1:
                audio = audio.squeeze()
            
            return audio.astype(np.float32)
    
    def get_stats(self):
        """Stats ASR"""
        return self.asr.get_stats()


class MimirASRPipeline:
    """
    Pipeline completo ASR per Mimir
    
    Gestisce:
    1. Ricezione audio da Moshi/Mimi
    2. Conversione formato
    3. Trascrizione Whisper
    4. Callback con testo
    """
    
    def __init__(
        self,
        whisper_config: Optional[WhisperConfig] = None,
        on_text_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            whisper_config: Config Whisper
            on_text_callback: Chiamato quando arriva testo trascritto
        """
        self.adapter = WhisperMimiAdapter(
            config=whisper_config,
            on_transcription=on_text_callback
        )
        self._running = False
        
    async def start(self):
        """Avvia pipeline"""
        self.adapter.initialize()
        self._running = True
        logger.info("✅ Mimir ASR Pipeline started")
    
    async def stop(self):
        """Ferma pipeline"""
        self._running = False
        self.adapter.shutdown()
        logger.info("Mimir ASR Pipeline stopped")
    
    async def process_audio_chunk(self, audio: np.ndarray) -> Optional[str]:
        """
        Processa chunk audio
        
        Args:
            audio: Audio chunk (24kHz da Mimi)
            
        Returns:
            Testo trascritto se disponibile
        """
        if not self._running:
            return None
        
        return await self.adapter.process_mimi_audio(audio)
    
    async def process_loop(self, audio_stream):
        """
        Loop principale di processing
        
        Args:
            audio_stream: Generator/AsyncIterator di chunk audio
        """
        async for audio_chunk in audio_stream:
            text = await self.process_audio_chunk(audio_chunk)
            if text:
                logger.info(f"📝 Trascrizione: {text}")
    
    def get_stats(self):
        """Stats pipeline"""
        return self.adapter.get_stats()


# ========================================
# TEST
# ========================================

async def test_adapter():
    """Test adapter"""
    print("=== Test Whisper Adapter ===\n")
    
    def on_text(text: str):
        print(f"📝 Callback: '{text}'")
    
    config = WhisperConfig(
        model_size="base",  # Base per test veloce
        language="it"
    )
    
    adapter = WhisperMimiAdapter(config=config, on_transcription=on_text)
    adapter.initialize()
    
    print("✅ Adapter inizializzato\n")
    
    # Simula audio 24kHz
    sample_rate_24k = 24000
    duration = 2.0  # 2 secondi
    
    # Audio sintetico (rumore)
    audio_24k = np.random.randn(int(sample_rate_24k * duration)).astype(np.float32) * 0.05
    
    print(f"Processing {duration}s audio @ 24kHz...")
    result = await adapter.process_mimi_audio(audio_24k)
    
    print(f"\nRisultato: {result}")
    
    # Stats
    print("\n--- Stats ---")
    stats = adapter.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    adapter.shutdown()
    print("\n✅ Test completato")


async def test_pipeline():
    """Test pipeline completo"""
    print("=== Test Mimir ASR Pipeline ===\n")
    
    transcriptions = []
    
    def on_text(text: str):
        transcriptions.append(text)
        print(f"✅ Trascrizione ricevuta: '{text}'")
    
    config = WhisperConfig(model_size="base", language="it")
    pipeline = MimirASRPipeline(whisper_config=config, on_text_callback=on_text)
    
    await pipeline.start()
    
    # Simula stream audio
    async def audio_generator():
        """Simula stream di chunk audio"""
        for i in range(3):
            # Chunk di 1 secondo @ 24kHz
            audio = np.random.randn(24000).astype(np.float32) * 0.1
            await asyncio.sleep(0.1)  # Simula delay
            yield audio
    
    print("Processing audio stream...\n")
    await pipeline.process_loop(audio_generator())
    
    await pipeline.stop()
    
    print(f"\n✅ Pipeline test completato - {len(transcriptions)} trascrizioni")


if __name__ == "__main__":
    # asyncio.run(test_adapter())
    asyncio.run(test_pipeline())
