python << 'EOF'
import numpy as np
import soundfile as sf
from pathlib import Path
from pydub import AudioSegment
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def merge_wav_files(input_dir, output_file, target_duration=60.0, sample_rate=22050):
    """
    Unisce file WAV per voice cloning
    
    Args:
        input_dir: Directory con file WAV
        output_file: File output unificato
        target_duration: Durata target in secondi (60s = 1 minuto)
        sample_rate: Sample rate target (22050 per XTTS)
    """
    input_path = Path(input_dir)
    wav_files = sorted(input_path.glob("*.wav"))
    
    if not wav_files:
        logger.error(f"Nessun file WAV trovato in {input_dir}")
        return None
    
    logger.info(f"Trovati {len(wav_files)} file WAV")
    
    # Carica e concatena
    combined = AudioSegment.empty()
    total_duration = 0
    
    for i, wav_file in enumerate(wav_files):
        try:
            audio = AudioSegment.from_wav(wav_file)
            
            # Converti a mono
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Resample a 22050Hz
            if audio.frame_rate != sample_rate:
                audio = audio.set_frame_rate(sample_rate)
            
            # Aggiungi
            combined += audio
            total_duration = len(combined) / 1000.0
            
            if i % 50 == 0:
                logger.info(f"Processati {i}/{len(wav_files)} file - Durata: {total_duration:.1f}s")
            
            # Stop se raggiungiamo target
            if total_duration >= target_duration:
                logger.info(f"Raggiunta durata target: {total_duration:.1f}s")
                break
                
        except Exception as e:
            logger.warning(f"Errore su {wav_file.name}: {e}")
            continue
    
    # Normalizza volume
    combined = combined.normalize()
    
    # Salva
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    combined.export(output_path, format="wav")
    
    final_duration = len(combined) / 1000.0
    logger.info(f"✅ Voice file creato: {output_path}")
    logger.info(f"   Durata: {final_duration:.1f}s")
    logger.info(f"   Sample rate: {sample_rate}Hz")
    
    return str(output_path)

# CONFIGURA QUI
INPUT_DIR = "~projects/mimir/data/voice_models"  # ← CAMBIA QUESTO
OUTPUT_FILE = "./data/voice_models/mimir_voice_master.wav"
TARGET_DURATION = 60.0  # 60 secondi (ottimale per XTTS)

print("=== Merge WAV Files per Voice Cloning ===\n")
result = merge_wav_files(INPUT_DIR, OUTPUT_FILE, TARGET_DURATION)

if result:
    print(f"\n✅ File pronto per voice cloning: {result}")
    print(f"\nConfigura in config/mimir/settings.yaml:")
    print(f"  speaker_wav: {result}")
    print(f"  use_custom_voice: true")
else:
    print("\n❌ Errore durante il merge")
EOF
