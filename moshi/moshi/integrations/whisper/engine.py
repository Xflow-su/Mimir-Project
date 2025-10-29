"""
Mimir - Whisper ASR Engine
Automatic Speech Recognition usando OpenAI Whisper
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
import numpy as np
import torch
import whisper
from queue import Queue
import threading

logger = logging.getLogger(__name__)


@dataclass
class WhisperConfig:
    """Configurazione Whisper"""
    model_size: str = "medium"  # tiny, base, small, medium, large
    language: str = "it"  # Italiano
    device: str = "cpu"  # cpu o cuda
    sample_rate: int = 16000
    
    # VAD (Voice Activity Detection) settings
    vad_enabled: bool = True
    vad_threshold: float = 0.02  # Soglia energia audio
    silence_duration: float = 1.5  # Secondi di silenzio per trigger trascrizione
    min_speech_duration: float = 0.3  # Minimo audio per considerarlo speech
    
    # Whisper parameters
    fp16: bool = False  # Use FP16 (solo con CUDA)
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0  # 0.0 = più deterministico
    
    # Performance
    chunk_length: int = 30  # Secondi per chunk
    no_speech_threshold: float = 0.6


class WhisperEngine:
    """
    Engine Whisper per trascrizione real-time
    
    Gestisce:
    - Caricamento modello Whisper
    - Buffer audio con VAD
    - Trascrizione incrementale
    - Detection silenzio
    """
    
    def __init__(self, config: Optional[WhisperConfig] = None):
        self.config = config or WhisperConfig()
        self.model: Optional[whisper.Whisper] = None
        self.device = torch.device(self.config.device)
        
        # Buffer audio
        self._audio_buffer = np.array([], dtype=np.float32)
        self._buffer_lock = threading.Lock()
        
        # VAD state
        self._silence_start: Optional[float] = None
        self._is_speech_active = False
        
        # Stats
        self._transcription_count = 0
        self._total_audio_seconds = 0.0
        
    def load_model(self):
        """Carica modello Whisper"""
        if self.model is not None:
            logger.info("Modello già caricato")
            return
        
        logger.info(f"Caricamento Whisper model: {self.config.model_size}")
        start = time.time()
        
        try:
            self.model = whisper.load_model(
                self.config.model_size,
                device=self.device
            )
            
            elapsed = time.time() - start
            logger.info(f"✅ Whisper caricato in {elapsed:.2f}s - Device: {self.device}")
            
        except Exception as e:
            logger.error(f"Errore caricamento Whisper: {e}")
            raise
    
    def append_audio(self, audio_chunk: np.ndarray):
        """
        Aggiungi audio al buffer
        
        Args:
            audio_chunk: Audio numpy array (float32, mono, 16kHz)
        """
        with self._buffer_lock:
            self._audio_buffer = np.concatenate([self._audio_buffer, audio_chunk])
    
    def get_buffer_duration(self) -> float:
        """Ritorna durata buffer in secondi"""
        with self._buffer_lock:
            return len(self._audio_buffer) / self.config.sample_rate
    
    def clear_buffer(self):
        """Svuota buffer audio"""
        with self._buffer_lock:
            self._audio_buffer = np.array([], dtype=np.float32)
            self._silence_start = None
            self._is_speech_active = False
    
    def _detect_voice_activity(self, audio: np.ndarray) -> bool:
        """
        Voice Activity Detection semplice basato su energia
        
        Args:
            audio: Chunk audio
            
        Returns:
            True se rileva voce
        """
        if not self.config.vad_enabled:
            return True
        
        # Calcola energia RMS
        rms = np.sqrt(np.mean(audio ** 2))
        return rms > self.config.vad_threshold
    
    def should_transcribe(self, current_audio: np.ndarray) -> bool:
        """
        Determina se è il momento di trascrivere
        
        Logic:
        1. Rileva se c'è speech nel chunk corrente
        2. Se no speech per silence_duration secondi → trascrivi
        3. Se buffer troppo lungo → trascrivi comunque
        
        Args:
            current_audio: Ultimo chunk audio ricevuto
            
        Returns:
            True se dovremmo trascrivere ora
        """
        has_voice = self._detect_voice_activity(current_audio)
        current_time = time.time()
        buffer_duration = self.get_buffer_duration()
        
        # Check 1: Buffer troppo lungo (30 secondi)
        if buffer_duration >= self.config.chunk_length:
            logger.debug("Trigger: buffer pieno")
            return True
        
        # Check 2: Audio troppo corto
        if buffer_duration < self.config.min_speech_duration:
            return False
        
        # Check 3: Gestione silenzio
        if has_voice:
            self._is_speech_active = True
            self._silence_start = None
        else:
            if self._is_speech_active:
                # Passaggio da speech a silenzio
                if self._silence_start is None:
                    self._silence_start = current_time
                else:
                    # Calcola durata silenzio
                    silence_duration = current_time - self._silence_start
                    if silence_duration >= self.config.silence_duration:
                        logger.debug(f"Trigger: silenzio {silence_duration:.2f}s")
                        return True
        
        return False
    
    async def transcribe_buffer(self) -> Optional[str]:
        """
        Trascrivi il contenuto del buffer corrente
        
        Returns:
            Testo trascritto o None se buffer vuoto/errore
        """
        if self.model is None:
            raise RuntimeError("Modello non caricato. Chiama load_model() prima.")
        
        with self._buffer_lock:
            if len(self._audio_buffer) == 0:
                return None
            
            audio_to_transcribe = self._audio_buffer.copy()
            duration = len(audio_to_transcribe) / self.config.sample_rate
            
            # Prepara per trascrizione
            # Whisper si aspetta float32 normalizzato tra -1 e 1
            audio_normalized = audio_to_transcribe.astype(np.float32)
            
            # Assicurati che sia nel range corretto
            max_val = np.abs(audio_normalized).max()
            if max_val > 1.0:
                audio_normalized = audio_normalized / max_val
        
        logger.debug(f"Trascrizione di {duration:.2f}s audio...")
        start = time.time()
        
        try:
            # Whisper transcription (blocking - da eseguire in thread)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    audio_normalized,
                    language=self.config.language,
                    fp16=self.config.fp16,
                    beam_size=self.config.beam_size,
                    best_of=self.config.best_of,
                    temperature=self.config.temperature,
                    no_speech_threshold=self.config.no_speech_threshold
                )
            )
            
            text = result["text"].strip()
            elapsed = time.time() - start
            
            # Stats
            self._transcription_count += 1
            self._total_audio_seconds += duration
            
            if text:
                logger.info(f"✅ Trascritto ({elapsed:.2f}s): '{text}'")
            else:
                logger.debug("Nessun testo rilevato")
            
            # Clear buffer dopo trascrizione
            self.clear_buffer()
            
            return text if text else None
            
        except Exception as e:
            logger.error(f"Errore trascrizione: {e}")
            self.clear_buffer()
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche utilizzo"""
        return {
            "transcription_count": self._transcription_count,
            "total_audio_seconds": self._total_audio_seconds,
            "buffer_duration": self.get_buffer_duration(),
            "is_speech_active": self._is_speech_active,
            "model_size": self.config.model_size,
            "device": str(self.device)
        }


# ========================================
# STREAMING WRAPPER
# ========================================

class WhisperStreamingASR:
    """
    Wrapper per ASR streaming real-time
    
    Usage:
        asr = WhisperStreamingASR()
        asr.start()
        
        # In loop audio:
        asr.process_audio(audio_chunk)
        
        # Quando serve trascrizione:
        if asr.has_transcription():
            text = await asr.get_transcription()
    """
    
    def __init__(self, config: Optional[WhisperConfig] = None):
        self.engine = WhisperEngine(config)
        self._transcription_queue: Queue = Queue()
        self._running = False
        
    def start(self):
        """Avvia engine"""
        self.engine.load_model()
        self._running = True
        logger.info("✅ Whisper Streaming ASR started")
    
    def stop(self):
        """Ferma engine"""
        self._running = False
        self.engine.clear_buffer()
        logger.info("Whisper Streaming ASR stopped")
    
    def process_audio(self, audio_chunk: np.ndarray) -> bool:
        """
        Processa chunk audio
        
        Args:
            audio_chunk: Audio numpy array
            
        Returns:
            True se ha triggerato una trascrizione
        """
        if not self._running:
            return False
        
        self.engine.append_audio(audio_chunk)
        return self.engine.should_transcribe(audio_chunk)
    
    async def get_transcription(self) -> Optional[str]:
        """
        Ottieni trascrizione (se disponibile)
        
        Returns:
            Testo trascritto o None
        """
        return await self.engine.transcribe_buffer()
    
    def get_stats(self) -> Dict[str, Any]:
        """Stats engine"""
        return self.engine.get_stats()


# ========================================
# TEST
# ========================================

async def test_whisper():
    """Test Whisper engine"""
    print("=== Test Whisper Engine ===\n")
    
    # Config
    config = WhisperConfig(
        model_size="medium",  # Usa 'base' se vuoi test più veloce
        language="it",
        device="cpu"
    )
    
    engine = WhisperEngine(config)
    engine.load_model()
    
    print("✅ Modello caricato\n")
    print("Parla nel microfono... (simulazione con audio sintetico)")
    
    # Simula audio (silenzio + rumore)
    sample_rate = 16000
    
    # Chunk 1: Silenzio
    silence = np.zeros(int(sample_rate * 0.5), dtype=np.float32)
    engine.append_audio(silence)
    print(f"Buffer: {engine.get_buffer_duration():.2f}s")
    
    # Chunk 2: "Speech" simulato (rumore)
    speech = np.random.randn(int(sample_rate * 2.0)).astype(np.float32) * 0.1
    engine.append_audio(speech)
    print(f"Buffer: {engine.get_buffer_duration():.2f}s")
    
    # Trascrizione
    print("\nTrascrizione...")
    text = await engine.transcribe_buffer()
    print(f"Risultato: {text}")
    
    # Stats
    print("\n--- Stats ---")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Test completato")


if __name__ == "__main__":
    asyncio.run(test_whisper())
