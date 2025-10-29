"""
Mimir - XTTS v2 Engine
Text-to-Speech usando Coqui XTTS v2 con voice cloning
"""

import asyncio
import logging
import time
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import numpy as np
import torch
from TTS.api import TTS
import soundfile as sf

logger = logging.getLogger(__name__)


@dataclass
class XTTSConfig:
    """Configurazione XTTS v2"""
    model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    language: str = "it"
    device: str = "cpu"  # cpu o cuda
    
    # Voice cloning
    speaker_wav: Optional[str] = None  # Path al file audio per cloning
    use_custom_voice: bool = False
    
    # Quality settings (OTTIMIZZATI per voice cloning)
    sample_rate: int = 22050  # XTTS output sample rate
    speed: float = 1.0  # Velocità parlato (0.5-2.0)
    temperature: float = 0.65  # ← RIDOTTO per più coerenza (era 0.75)
    length_penalty: float = 1.0
    repetition_penalty: float = 5.0  # ← AUMENTATO per evitare ripetizioni (era 2.0)
    top_k: int = 50
    top_p: float = 0.85
    
    # Voice cloning quality (NUOVO)
    enable_text_splitting: bool = True
    gpt_cond_len: int = 30  # Lunghezza conditioning (più alto = più simile alla voce)
    gpt_cond_chunk_len: int = 4  # Chunk size per conditioning
    max_ref_length: int = 60  # Max secondi reference audio da usare


class XTTSEngine:
    """
    Engine XTTS v2 per sintesi vocale con voice cloning
    
    Features:
    - Voice cloning da file audio
    - Sintesi multilingua (italiano)
    - Streaming audio
    - Qualità professionale
    """
    
    def __init__(self, config: Optional[XTTSConfig] = None):
        self.config = config or XTTSConfig()
        self.tts: Optional[TTS] = None
        self.device = torch.device(self.config.device)
        
        # Voice cloning
        self._speaker_embedding: Optional[np.ndarray] = None
        self._speaker_wav_loaded = False
        
        # Stats
        self._synthesis_count = 0
        self._total_characters = 0
        
    def load_model(self):
        """Carica modello XTTS v2"""
        if self.tts is not None:
            logger.info("Modello XTTS già caricato")
            return
        
        logger.info(f"Caricamento XTTS v2...")
        start = time.time()
        
        try:
            # Inizializza TTS
            self.tts = TTS(
                model_name=self.config.model_name,
                progress_bar=True
            ).to(self.device)
            
            elapsed = time.time() - start
            logger.info(f"✅ XTTS v2 caricato in {elapsed:.2f}s - Device: {self.device}")
            
            # Carica speaker voice se specificato
            if self.config.use_custom_voice and self.config.speaker_wav:
                self._load_speaker_voice()
            
        except Exception as e:
            logger.error(f"Errore caricamento XTTS: {e}")
            raise
    
    def _load_speaker_voice(self):
        """Carica voce speaker per cloning"""
        if not self.config.speaker_wav:
            logger.warning("speaker_wav non specificato, uso voce default")
            return
        
        speaker_path = Path(self.config.speaker_wav)
        if not speaker_path.exists():
            logger.error(f"File speaker non trovato: {speaker_path}")
            return
        
        logger.info(f"Caricamento voce speaker: {speaker_path}")
        
        try:
            # XTTS caricherà automaticamente il file al momento della sintesi
            self._speaker_wav_loaded = True
            logger.info("✅ Voce speaker pronta per cloning")
            
        except Exception as e:
            logger.error(f"Errore caricamento speaker voice: {e}")
            self._speaker_wav_loaded = False
    
    def _split_text_into_sentences(self, text: str) -> List[str]:
        """
        Split testo in frasi per sintesi incrementale
        
        Args:
            text: Testo completo
            
        Returns:
            Lista di frasi
        """
        if not self.config.enable_text_splitting:
            return [text]
        
        # Split semplice su punteggiatura
        import re
        sentences = re.split(r'([.!?]+\s+)', text)
        
        # Ricombina punteggiatura con frase
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])
        
        # Aggiungi ultima frase se presente
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])
        
        # Rimuovi frasi vuote
        return [s.strip() for s in result if s.strip()]
    
    async def synthesize(self, text: str) -> Optional[np.ndarray]:
        """
        Sintetizza testo in audio
        
        Args:
            text: Testo da sintetizzare
            
        Returns:
            Audio numpy array (float32, mono, 22050Hz) o None
        """
        if self.tts is None:
            raise RuntimeError("Modello non caricato. Chiama load_model() prima.")
        
        if not text or not text.strip():
            logger.warning("Testo vuoto, skip sintesi")
            return None
        
        text = text.strip()
        logger.debug(f"Sintesi: '{text[:50]}...'")
        start = time.time()
        
        try:
            # Sintesi (blocking - esegui in executor)
            loop = asyncio.get_event_loop()
            
            if self.config.use_custom_voice and self._speaker_wav_loaded:
                # Voice cloning con file speaker - Approccio corretto per XTTS v2
                logger.info(f"Voice cloning con: {self.config.speaker_wav}")
                
                wav = await loop.run_in_executor(
                    None,
                    lambda: self.tts.tts(
                        text=text,
                        language=self.config.language,
                        speaker_wav=self.config.speaker_wav,
                        # XTTS non accetta questi parametri in voice cloning mode
                        # temperature=self.config.temperature,
                        # length_penalty=self.config.length_penalty,
                    )
                )
            else:
                # Prova con speaker di default se multi-speaker
                speakers = self.tts.speakers if hasattr(self.tts, 'speakers') else []
                
                if speakers and len(speakers) > 0:
                    # Usa primo speaker disponibile
                    logger.info(f"Usando speaker: {speakers[0]}")
                    wav = await loop.run_in_executor(
                        None,
                        lambda: self.tts.tts(
                            text=text,
                            language=self.config.language,
                            speaker=speakers[0]
                        )
                    )
                else:
                    # Ultimo tentativo: sintesi senza speaker
                    logger.warning("Tentativo sintesi senza speaker specificato")
                    wav = await loop.run_in_executor(
                        None,
                        lambda: self.tts.tts(
                            text=text,
                            language=self.config.language
                        )
                    )
            
            elapsed = time.time() - start
            
            # Converti a numpy se necessario
            if isinstance(wav, list):
                wav = np.array(wav, dtype=np.float32)
            elif torch.is_tensor(wav):
                wav = wav.cpu().numpy().astype(np.float32)
            
            # Stats
            self._synthesis_count += 1
            self._total_characters += len(text)
            
            duration = len(wav) / self.config.sample_rate
            logger.info(f"✅ Sintetizzato {len(text)} char in {elapsed:.2f}s → {duration:.2f}s audio")
            
            return wav
            
        except Exception as e:
            logger.error(f"Errore sintesi TTS: {e}")
            return None
    
    async def synthesize_streaming(self, text: str):
        """
        Sintetizza testo con streaming (frase per frase)
        
        Args:
            text: Testo completo
            
        Yields:
            Chunk audio numpy array
        """
        sentences = self._split_text_into_sentences(text)
        
        logger.debug(f"Sintesi streaming: {len(sentences)} frasi")
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            logger.debug(f"Frase {i+1}/{len(sentences)}: '{sentence[:40]}...'")
            
            audio = await self.synthesize(sentence)
            if audio is not None:
                yield audio
    
    def save_audio(self, audio: np.ndarray, filepath: str):
        """
        Salva audio su file
        
        Args:
            audio: Audio numpy array
            filepath: Path output
        """
        try:
            sf.write(filepath, audio, self.config.sample_rate)
            logger.info(f"✅ Audio salvato: {filepath}")
        except Exception as e:
            logger.error(f"Errore salvataggio audio: {e}")
    
    def get_stats(self):
        """Ritorna statistiche utilizzo"""
        return {
            "synthesis_count": self._synthesis_count,
            "total_characters": self._total_characters,
            "custom_voice_loaded": self._speaker_wav_loaded,
            "model": self.config.model_name,
            "device": str(self.device),
            "sample_rate": self.config.sample_rate
        }


# ========================================
# VOICE CLONING HELPER
# ========================================

def create_speaker_voice(
    audio_file: str,
    output_dir: str = "./data/voice_models",
    voice_name: str = "mimir_voice"
) -> str:
    """
    Prepara file audio per voice cloning
    
    Args:
        audio_file: Path al file audio sorgente
        output_dir: Directory output
        voice_name: Nome della voce
        
    Returns:
        Path al file processato
    """
    from pydub import AudioSegment
    
    logger.info(f"Processing voice file: {audio_file}")
    
    # Crea output dir
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Carica audio
    audio = AudioSegment.from_file(audio_file)
    
    # Converti a mono 22050Hz
    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(22050)
    
    # Normalizza volume
    audio = audio.normalize()
    
    # Salva
    output_file = output_path / f"{voice_name}.wav"
    audio.export(output_file, format="wav")
    
    logger.info(f"✅ Voice file pronto: {output_file}")
    return str(output_file)


# ========================================
# TEST
# ========================================

async def test_xtts():
    """Test XTTS engine"""
    print("=== Test XTTS Engine ===\n")
    
    # ⚠️ IMPORTANTE: Abilita voice cloning
    config = XTTSConfig(
        language="it",
        device="cpu",
        use_custom_voice=True,  # ← ABILITATO
        speaker_wav="./data/voice_models/mimir_voice_1hour.wav"  # ← PATH FILE
    )
    
    engine = XTTSEngine(config)
    engine.load_model()
    
    print("✅ Modello caricato\n")
    
    # Test sintesi
    test_text = "Salve, cercatore di conoscenza. Sono Mimir, custode dell'antica saggezza norrena."
    
    print(f"Sintesi: '{test_text}'")
    audio = await engine.synthesize(test_text)
    
    if audio is not None:
        print(f"✅ Audio generato: {len(audio)} samples, {len(audio)/22050:.2f}s")
        
        # Salva per test
        output_file = "/tmp/mimir_test.wav"
        engine.save_audio(audio, output_file)
        print(f"Audio salvato: {output_file}")
    
    # Stats
    print("\n--- Stats ---")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Test completato")


async def test_streaming():
    """Test sintesi streaming"""
    print("=== Test XTTS Streaming ===\n")
    
    # ⚠️ IMPORTANTE: Abilita voice cloning per test
    config = XTTSConfig(
        language="it",
        device="cpu",
        use_custom_voice=True,  # ← ABILITATO
        speaker_wav="./data/voice_models/mimir_voice_1hour.wav"  # ← PATH FILE
    )
    
    engine = XTTSEngine(config)
    engine.load_model()
    
    text = "Salve, viandante. La saggezza antica insegna che la conoscenza è il più prezioso dei tesori. Cosa cerchi oggi?"
    
    print(f"Sintesi streaming: '{text}'\n")
    
    all_audio = []
    chunk_count = 0
    
    async for audio_chunk in engine.synthesize_streaming(text):
        chunk_count += 1
        print(f"Chunk {chunk_count}: {len(audio_chunk)} samples")
        all_audio.append(audio_chunk)
    
    # Concatena tutto
    if all_audio:
        complete_audio = np.concatenate(all_audio)
        print(f"\n✅ Audio completo: {len(complete_audio)} samples, {len(complete_audio)/22050:.2f}s")
        
        # Salva
        output_file = "/tmp/mimir_streaming_test.wav"
        engine.save_audio(complete_audio, output_file)
        print(f"Salvato: {output_file}")
    
    print("\n✅ Test streaming completato")


if __name__ == "__main__":
    # asyncio.run(test_xtts())
    asyncio.run(test_streaming())
