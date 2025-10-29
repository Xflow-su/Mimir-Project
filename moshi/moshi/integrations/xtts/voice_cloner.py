"""
Mimir - Voice Cloner
Utility per creare e gestire voci custom per XTTS v2
"""

import logging
import os
from pathlib import Path
from typing import Optional, List
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from pydub.effects import normalize

logger = logging.getLogger(__name__)


class VoiceCloner:
    """
    Helper per creare voci custom per Mimir
    
    Process:
    1. Registra 10-30 secondi di audio pulito
    2. Processa audio (mono, 22050Hz, normalizza)
    3. Valida qualità
    4. Salva per uso con XTTS
    """
    
    def __init__(self, output_dir: str = "./data/voice_models"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def process_voice_file(
        self,
        input_file: str,
        voice_name: str = "mimir_voice",
        validate: bool = True
    ) -> str:
        """
        Processa file audio per voice cloning
        
        Args:
            input_file: Path al file audio sorgente (wav, mp3, etc.)
            voice_name: Nome della voce
            validate: Se True, valida qualità audio
            
        Returns:
            Path al file processato
        """
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"File non trovato: {input_file}")
        
        logger.info(f"Processing voice: {input_path.name}")
        
        # Carica audio
        try:
            audio = AudioSegment.from_file(str(input_path))
        except Exception as e:
            raise ValueError(f"Impossibile caricare audio: {e}")
        
        # Info originale
        logger.info(f"Audio originale: {len(audio)}ms, {audio.channels}ch, {audio.frame_rate}Hz")
        
        # Converti a mono
        if audio.channels > 1:
            audio = audio.set_channels(1)
            logger.info("Convertito a mono")
        
        # Resample a 22050Hz (XTTS requirement)
        if audio.frame_rate != 22050:
            audio = audio.set_frame_rate(22050)
            logger.info("Resampled a 22050Hz")
        
        # Normalizza volume
        audio = normalize(audio)
        logger.info("Volume normalizzato")
        
        # Rimuovi silenzio iniziale/finale
        audio = self._trim_silence(audio)
        
        # Valida se richiesto
        if validate:
            is_valid, issues = self._validate_audio(audio)
            if not is_valid:
                logger.warning(f"Audio ha problemi: {', '.join(issues)}")
                logger.warning("Procedo comunque, ma qualità voice cloning potrebbe essere ridotta")
        
        # Salva
        output_file = self.output_dir / f"{voice_name}.wav"
        audio.export(str(output_file), format="wav")
        
        duration = len(audio) / 1000.0
        logger.info(f"✅ Voice file pronto: {output_file} ({duration:.1f}s)")
        
        return str(output_file)
    
    def _trim_silence(
        self,
        audio: AudioSegment,
        silence_thresh: int = -50,  # dB
        chunk_size: int = 10  # ms
    ) -> AudioSegment:
        """Rimuovi silenzio iniziale e finale"""
        # Trim start
        start_trim = 0
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i+chunk_size]
            if chunk.dBFS > silence_thresh:
                start_trim = i
                break
        
        # Trim end
        end_trim = len(audio)
        for i in range(len(audio), 0, -chunk_size):
            chunk = audio[max(0, i-chunk_size):i]
            if chunk.dBFS > silence_thresh:
                end_trim = i
                break
        
        trimmed = audio[start_trim:end_trim]
        
        if start_trim > 0 or end_trim < len(audio):
            logger.info(f"Silenzio rimosso: {start_trim}ms inizio, {len(audio)-end_trim}ms fine")
        
        return trimmed
    
    def _validate_audio(self, audio: AudioSegment) -> tuple[bool, List[str]]:
        """
        Valida qualità audio per voice cloning
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check 1: Durata (10-30 secondi ideale)
        duration = len(audio) / 1000.0
        if duration < 6:
            issues.append(f"Audio troppo corto ({duration:.1f}s, minimo 6s)")
        elif duration > 60:
            issues.append(f"Audio troppo lungo ({duration:.1f}s, massimo 60s consigliato)")
        
        # Check 2: Volume
        db_level = audio.dBFS
        if db_level < -30:
            issues.append(f"Volume troppo basso ({db_level:.1f}dB)")
        elif db_level > -3:
            issues.append(f"Volume troppo alto ({db_level:.1f}dB, rischio clipping)")
        
        # Check 3: Silenzio
        silence_chunks = 0
        chunk_size = 100  # ms
        silence_thresh = -50  # dB
        
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i+chunk_size]
            if chunk.dBFS < silence_thresh:
                silence_chunks += 1
        
        silence_ratio = silence_chunks / (len(audio) / chunk_size)
        if silence_ratio > 0.3:
            issues.append(f"Troppo silenzio ({silence_ratio*100:.0f}%)")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def create_from_recording(
        self,
        duration: int = 15,
        voice_name: str = "mimir_voice",
        device_index: Optional[int] = None
    ) -> str:
        """
        Registra audio dal microfono e crea voice file
        
        Args:
            duration: Durata registrazione (secondi)
            voice_name: Nome voce
            device_index: Device microfono (None = default)
            
        Returns:
            Path al voice file creato
        """
        import sounddevice as sd
        
        logger.info(f"Inizio registrazione: {duration}s...")
        logger.info("Parla chiaramente nel microfono!")
        
        sample_rate = 22050
        
        try:
            # Registra
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='float32',
                device=device_index
            )
            
            sd.wait()  # Aspetta fine registrazione
            
            logger.info("✅ Registrazione completata")
            
            # Salva temporaneamente
            temp_file = self.output_dir / "temp_recording.wav"
            sf.write(temp_file, recording, sample_rate)
            
            # Processa
            output_file = self.process_voice_file(
                str(temp_file),
                voice_name=voice_name,
                validate=True
            )
            
            # Rimuovi temp
            temp_file.unlink()
            
            return output_file
            
        except Exception as e:
            logger.error(f"Errore registrazione: {e}")
            raise
    
    def list_voices(self) -> List[str]:
        """Lista voci disponibili"""
        voices = list(self.output_dir.glob("*.wav"))
        return [v.stem for v in voices]
    
    def get_voice_path(self, voice_name: str) -> Optional[str]:
        """Ottieni path completo di una voce"""
        voice_file = self.output_dir / f"{voice_name}.wav"
        if voice_file.exists():
            return str(voice_file)
        return None


# ========================================
# CLI HELPER
# ========================================

def interactive_voice_setup():
    """Setup interattivo voce Mimir"""
    print("=== Setup Voce Mimir ===\n")
    
    cloner = VoiceCloner()
    
    print("Opzioni:")
    print("1. Registra nuova voce dal microfono")
    print("2. Usa file audio esistente")
    
    choice = input("\nScelta (1/2): ").strip()
    
    if choice == "1":
        # Registrazione
        print("\nPreparati a registrare!")
        print("Tips:")
        print("- Ambiente silenzioso")
        print("- Parla chiaramente e con calma")
        print("- Mantieni tono costante")
        print("- 15 secondi sono sufficienti")
        
        input("\nPremi INVIO quando sei pronto...")
        
        try:
            voice_file = cloner.create_from_recording(
                duration=15,
                voice_name="mimir_voice"
            )
            print(f"\n✅ Voce creata: {voice_file}")
            print(f"\nConfigura in settings.yaml:")
            print(f"  speaker_wav: {voice_file}")
            print(f"  use_custom_voice: true")
            
        except Exception as e:
            print(f"\n❌ Errore: {e}")
    
    elif choice == "2":
        # File esistente
        audio_file = input("\nPath al file audio: ").strip()
        
        if not Path(audio_file).exists():
            print(f"❌ File non trovato: {audio_file}")
            return
        
        try:
            voice_file = cloner.process_voice_file(
                audio_file,
                voice_name="mimir_voice"
            )
            print(f"\n✅ Voce creata: {voice_file}")
            print(f"\nConfigura in settings.yaml:")
            print(f"  speaker_wav: {voice_file}")
            print(f"  use_custom_voice: true")
            
        except Exception as e:
            print(f"\n❌ Errore: {e}")
    
    else:
        print("Scelta non valida")


# ========================================
# TEST
# ========================================

def test_voice_cloner():
    """Test voice cloner"""
    print("=== Test Voice Cloner ===\n")
    
    cloner = VoiceCloner()
    
    # Lista voci
    voices = cloner.list_voices()
    print(f"Voci esistenti: {voices}\n")
    
    # Test validazione con audio sintetico
    print("Creazione audio test...")
    
    # Genera audio sintetico (5 secondi, 22050Hz)
    sample_rate = 22050
    duration = 5.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * 440 * t) * 0.3  # 440Hz sine wave
    
    # Salva temp
    temp_file = "/tmp/test_voice.wav"
    sf.write(temp_file, audio, sample_rate)
    
    # Processa
    try:
        output = cloner.process_voice_file(
            temp_file,
            voice_name="test_voice",
            validate=True
        )
        print(f"✅ Voice processata: {output}")
    except Exception as e:
        print(f"❌ Errore: {e}")
    
    print("\n✅ Test completato")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_voice_setup()
    else:
        test_voice_cloner()
