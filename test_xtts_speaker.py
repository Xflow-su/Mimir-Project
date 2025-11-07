# test_xtts_speaker.py
from pathlib import Path

# FIX: parent solo una volta (il file è nella root)
project_root = Path(__file__).parent  # ← Era .parent.parent
speaker_wav = project_root / "data" / "voice_models" / "voce_mimir" / "mimir_voice_master.wav"

print(f"Project root: {project_root}")
print(f"Speaker WAV: {speaker_wav}")
print(f"Esiste: {speaker_wav.exists()}")

if speaker_wav.exists():
    config = XTTSConfig(
        device="cpu",
        language="it",
        speaker_wav=str(speaker_wav),
        use_custom_voice=True
    )
    
    engine = XTTSEngine(config)
    engine.load_model()
    
    print(f"✅ Config caricata!")
    print(f"   Speaker: {config.speaker_wav}")
    print(f"   Use custom: {config.use_custom_voice}")
else:
    print("❌ File non trovato!")
    # Lista file disponibili
    voice_dir = project_root / "data" / "voice_models"
    print(f"\nFile in {voice_dir}:")
    if voice_dir.exists():
        for f in voice_dir.rglob("*.wav"):
            print(f"  - {f}")
