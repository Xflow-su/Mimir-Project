"""
Mimir - XTTS Adapter
Adapter per integrare XTTS nel pipeline audio di Moshi
"""

import asyncio
import logging
from typing import Optional, AsyncIterator
import numpy as np
import torch

from .engine import XTTSEngine, XTTSConfig

logger = logging.getLogger(__name__)


class XTTSMimiAdapter:
    """
    Adapter che converte testo da LLM in audio compatibile con Mimi
    
    Moshi/Mimi usa:
    - Sample rate: 24kHz
    - Formato: codici audio compressi
    
    XTTS genera:
    - Sample rate: 22050Hz
    - Formato: audio raw float32
    
    Questo adapter gestisce la conversione.
    """
    
    def __init__(
        self,
        config: Optional[XTTSConfig] = None,
        mimi_sample_rate: int = 24000
    ):
        """
        Args:
            config: Config XTTS
            mimi_sample_rate: Sample rate target per Mimi (24kHz)
        """
        self.config = config or XTTSConfig()
        self.mimi_sample_rate = mimi_sample_rate
        self.xtts_sample_rate = self.config.sample_rate
        
        self.engine = XTTSEngine(config)
        self._initialized = False
        
    def initialize(self):
        """Inizializza XTTS"""
        if self._initialized:
            return
        
        logger.info("Inizializzazione XTTS engine...")
        self.engine.load_model()
        self._initialized = True
        logger.info("✅ XTTS engine pronto")
    
    def shutdown(self):
        """Shutdown XTTS"""
        self._initialized = False
    
    def resample_audio(
        self,
        audio: np.ndarray,
        from_sr: int,
        to_sr: int
    ) -> np.ndarray:
        """
        Resample audio
        
        Args:
            audio: Audio array
            from_sr: Sample rate originale
            to_sr: Sample rate target
            
        Returns:
            Audio resampleato
        """
        if from_sr == to_sr:
            return audio
        
        # Resampling lineare (per produzione: usare librosa)
        duration = len(audio) / from_sr
        new_length = int(duration * to_sr)
        
        indices = np.linspace(0, len(audio) - 1, new_length)
        resampled = np.interp(indices, np.arange(len(audio)), audio)
        
        return resampled.astype(np.float32)
    
    async def text_to_audio(
        self,
        text: str,
        resample_to_mimi: bool = True
    ) -> Optional[np.ndarray]:
        """
        Converte testo in audio compatibile con Mimi
        
        Args:
            text: Testo da sintetizzare
            resample_to_mimi: Se True, resample a 24kHz per Mimi
            
        Returns:
            Audio numpy array (24kHz se resample_to_mimi=True)
        """
        if not self._initialized:
            raise RuntimeError("Adapter non inizializzato. Chiama initialize()")
        
        # Sintetizza con XTTS (22050Hz)
        audio_22k = await self.engine.synthesize(text)
        
        if audio_22k is None:
            return None
        
        # Resample a 24kHz se richiesto
        if resample_to_mimi:
            audio_24k = self.resample_audio(
                audio_22k,
                from_sr=self.xtts_sample_rate,
                to_sr=self.mimi_sample_rate
            )
            return audio_24k
        
        return audio_22k
    
    async def text_to_audio_streaming(
        self,
        text: str,
        resample_to_mimi: bool = True
    ) -> AsyncIterator[np.ndarray]:
        """
        Sintetizza testo in streaming (frase per frase)
        
        Args:
            text: Testo completo
            resample_to_mimi: Resample a 24kHz
            
        Yields:
            Chunk audio
        """
        if not self._initialized:
            raise RuntimeError("Adapter non inizializzato")
        
        async for audio_chunk in self.engine.synthesize_streaming(text):
            if resample_to_mimi:
                audio_chunk = self.resample_audio(
                    audio_chunk,
                    from_sr=self.xtts_sample_rate,
                    to_sr=self.mimi_sample_rate
                )
            yield audio_chunk
    
    def encode_for_mimi(self, audio: np.ndarray, mimi_encoder) -> torch.Tensor:
        """
        Encode audio in codici Mimi
        
        Args:
            audio: Audio numpy array (24kHz)
            mimi_encoder: Encoder Mimi
            
        Returns:
            Codici audio tensor
        """
        # Converti a tensor
        if not isinstance(audio, torch.Tensor):
            audio_tensor = torch.from_numpy(audio).float()
        else:
            audio_tensor = audio
        
        # Assicurati dimensioni corrette (batch, channels, samples)
        if audio_tensor.ndim == 1:
            audio_tensor = audio_tensor.unsqueeze(0).unsqueeze(0)
        elif audio_tensor.ndim == 2:
            audio_tensor = audio_tensor.unsqueeze(0)
        
        # Encode
        with torch.no_grad():
            codes = mimi_encoder.encode(audio_tensor)
        
        return codes
    
    def get_stats(self):
        """Stats engine"""
        return self.engine.get_stats()


class MimirTTSPipeline:
    """
    Pipeline completo TTS per Mimir
    
    Gestisce:
    1. Ricezione testo da LLM
    2. Sintesi audio con XTTS
    3. Conversione a formato Mimi
    4. Output audio
    """
    
    def __init__(
        self,
        xtts_config: Optional[XTTSConfig] = None,
        enable_streaming: bool = True
    ):
        """
        Args:
            xtts_config: Configurazione XTTS
            enable_streaming: Abilita sintesi streaming
        """
        self.adapter = XTTSMimiAdapter(config=xtts_config)
        self.enable_streaming = enable_streaming
        self._running = False
        
    async def start(self):
        """Avvia pipeline"""
        self.adapter.initialize()
        self._running = True
        logger.info("✅ Mimir TTS Pipeline started")
    
    async def stop(self):
        """Ferma pipeline"""
        self._running = False
        self.adapter.shutdown()
        logger.info("Mimir TTS Pipeline stopped")
    
    async def synthesize(self, text: str) -> Optional[np.ndarray]:
        """
        Sintetizza testo in audio
        
        Args:
            text: Testo da sintetizzare
            
        Returns:
            Audio 24kHz
        """
        if not self._running:
            return None
        
        return await self.adapter.text_to_audio(text, resample_to_mimi=True)
    
    async def synthesize_streaming(self, text: str) -> AsyncIterator[np.ndarray]:
        """
        Sintetizza con streaming
        
        Args:
            text: Testo
            
        Yields:
            Chunk audio 24kHz
        """
        if not self._running:
            return
        
        async for chunk in self.adapter.text_to_audio_streaming(
            text,
            resample_to_mimi=True
        ):
            yield chunk
    
    def get_stats(self):
        """Stats pipeline"""
        return self.adapter.get_stats()


# ========================================
# TEST
# ========================================

async def test_adapter():
    """Test XTTS adapter"""
    print("=== Test XTTS Adapter ===\n")
    
    config = XTTSConfig(
        language="it",
        device="cpu",
        use_custom_voice=False
    )
    
    adapter = XTTSMimiAdapter(config=config)
    adapter.initialize()
    
    print("✅ Adapter inizializzato\n")
    
    # Test sintesi
    text = "Salve, viandante. La saggezza ti accompagni."
    
    print(f"Sintesi: '{text}'")
    audio = await adapter.text_to_audio(text, resample_to_mimi=True)
    
    if audio is not None:
        print(f"✅ Audio generato: {len(audio)} samples @ 24kHz")
        print(f"   Durata: {len(audio)/24000:.2f}s")
    
    # Stats
    print("\n--- Stats ---")
    stats = adapter.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    adapter.shutdown()
    print("\n✅ Test completato")


async def test_pipeline():
    """Test pipeline completo"""
    print("=== Test Mimir TTS Pipeline ===\n")
    
    config = XTTSConfig(language="it", device="cpu")
    pipeline = MimirTTSPipeline(xtts_config=config, enable_streaming=True)
    
    await pipeline.start()
    
    # Test 1: Sintesi normale
    print("Test 1: Sintesi normale")
    text1 = "Ben ritrovato, cercatore."
    audio1 = await pipeline.synthesize(text1)
    
    if audio1 is not None:
        print(f"✅ Audio: {len(audio1)} samples, {len(audio1)/24000:.2f}s\n")
    
    # Test 2: Streaming
    print("Test 2: Sintesi streaming")
    text2 = "La conoscenza è il filo che tesse il destino. Ogni domanda apre nuove porte."
    
    chunk_count = 0
    total_samples = 0
    
    async for chunk in pipeline.synthesize_streaming(text2):
        chunk_count += 1
        total_samples += len(chunk)
        print(f"  Chunk {chunk_count}: {len(chunk)} samples")
    
    print(f"✅ Streaming: {chunk_count} chunks, {total_samples} samples totali")
    print(f"   Durata: {total_samples/24000:.2f}s\n")
    
    await pipeline.stop()
    
    print("✅ Pipeline test completato")


if __name__ == "__main__":
    # asyncio.run(test_adapter())
    asyncio.run(test_pipeline())
