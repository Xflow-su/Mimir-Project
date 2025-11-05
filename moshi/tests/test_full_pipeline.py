#!/usr/bin/env python3
"""
Test completo della pipeline MIMIR: Audio → Whisper → Ollama → XTTS → Audio
"""

import sys
import os
import asyncio
from pathlib import Path

# Aggiungi il path del progetto
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from moshi.moshi.integrations.whisper.whisper_integration import WhisperTranscriber
from moshi.moshi.integrations.ollama.ollama_integration import OllamaClient
from moshi.moshi.integrations.xtts.voice_cloner import VoiceCloner


async def test_full_pipeline():
    """Test completo della pipeline MIMIR"""
    
    print("=" * 60)
    print("🧠 MIMIR - Test Pipeline Completa")
    print("=" * 60)
    
    # Percorsi
    voice_sample = project_root / "data" / "voice_models" / "voce_mimir" / "mimir_voice_master.wav"
    output_dir = project_root / "data" / "test_outputs"
    output_dir.mkdir(exist_ok=True)
    
    # === STEP 1: Inizializzazione Componenti ===
    print("\n[1/5] 🔧 Inizializzazione componenti...")
    
    try:
        # Whisper
        print("   └─ Caricamento Whisper (medium)...")
        whisper = WhisperTranscriber(model_size="medium")
        print("   ✅ Whisper pronto")
        
        # Ollama
        print("   └─ Connessione Ollama (llama3.2:3b)...")
        ollama = OllamaClient(model="llama3.2:3b")
        print("   ✅ Ollama pronto")
        
        # XTTS
        print("   └─ Caricamento XTTS v2 + Voice Clone...")
        xtts = VoiceCloner()
        voices = xtts.list_voices()
        print(f"   ✅ XTTS pronto ({len(voices)} voci disponibili)")
        
    except Exception as e:
        print(f"   ❌ ERRORE nell'inizializzazione: {e}")
        return False
    
    # === STEP 2: Test con Input Audio (Whisper) ===
    print("\n[2/5] 🎤 Test Speech-to-Text (Whisper)...")
    
    # Verifica se abbiamo un file audio di test
    if voice_sample.exists():
        print(f"   └─ Trascrizione di: {voice_sample.name}")
        try:
            transcription = whisper.transcribe(str(voice_sample))
            print(f"   ✅ Trascritto: \"{transcription[:100]}...\"")
            test_input = transcription[:200]  # Usa primi 200 char
        except Exception as e:
            print(f"   ⚠️  Errore trascrizione: {e}")
            print("   └─ Uso input testuale di fallback")
            test_input = "Ciao, come stai oggi?"
    else:
        print("   ⚠️  File audio non trovato, uso input testuale")
        test_input = "Ciao, come stai oggi?"
    
    # === STEP 3: Test LLM (Ollama) ===
    print("\n[3/5] 🧠 Test LLM (Ollama)...")
    print(f"   └─ Input: \"{test_input}\"")
    
    try:
        response = await ollama.generate(
            prompt=test_input,
            system_prompt="Sei MIMIR, un assistente vocale amichevole e conciso. Rispondi in modo naturale e breve."
        )
        print(f"   ✅ Risposta LLM: \"{response[:150]}...\"")
    except Exception as e:
        print(f"   ❌ ERRORE Ollama: {e}")
        return False
    
    # === STEP 4: Test TTS (XTTS) ===
    print("\n[4/5] 🔊 Test Text-to-Speech (XTTS)...")
    
    output_audio = output_dir / "test_response.wav"
    
    try:
        print(f"   └─ Sintesi di {len(response)} caratteri...")
        audio_path = xtts.clone_voice(
            text=response[:500],  # Limita a 500 char per test veloce
            reference_audio=str(voice_sample),
            output_path=str(output_audio)
        )
        print(f"   ✅ Audio generato: {audio_path}")
        
        # Verifica dimensione file
        size_kb = Path(audio_path).stat().st_size / 1024
        print(f"   └─ Dimensione: {size_kb:.1f} KB")
        
    except Exception as e:
        print(f"   ❌ ERRORE XTTS: {e}")
        return False
    
    # === STEP 5: Riepilogo ===
    print("\n[5/5] 📊 Riepilogo Test")
    print("=" * 60)
    print(f"✅ INPUT:  \"{test_input}\"")
    print(f"✅ OUTPUT: \"{response[:100]}...\"")
    print(f"✅ AUDIO:  {output_audio}")
    print("=" * 60)
    print("\n🎉 PIPELINE COMPLETA FUNZIONANTE!")
    print(f"\nPuoi ascoltare la risposta con:")
    print(f"  aplay {output_audio}")
    print(f"  # oppure")
    print(f"  vlc {output_audio}")
    
    return True


async def quick_test():
    """Test rapido solo Ollama → XTTS (salta Whisper)"""
    
    print("=" * 60)
    print("🧠 MIMIR - Test Rapido (Ollama + XTTS)")
    print("=" * 60)
    
    voice_sample = project_root / "data" / "voice_models" / "voce_mimir" / "mimir_voice_master.wav"
    output_dir = project_root / "data" / "test_outputs"
    output_dir.mkdir(exist_ok=True)
    
    print("\n[1/3] Inizializzazione...")
    ollama = OllamaClient(model="llama3.2:3b")
    xtts = VoiceCloner()
    print("✅ Componenti pronti")
    
    print("\n[2/3] Generazione risposta LLM...")
    response = await ollama.generate(
        prompt="Presentati brevemente come MIMIR, un assistente vocale",
        system_prompt="Sei MIMIR. Rispondi in 2-3 frasi."
    )
    print(f"✅ Risposta: {response}")
    
    print("\n[3/3] Sintesi vocale...")
    output_audio = output_dir / "test_quick.wav"
    audio_path = xtts.clone_voice(
        text=response,
        reference_audio=str(voice_sample),
        output_path=str(output_audio)
    )
    print(f"✅ Audio: {audio_path}")
    print(f"\n🎉 Test completato! Ascolta con: aplay {output_audio}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test pipeline MIMIR")
    parser.add_argument("--quick", action="store_true", help="Test rapido (skip Whisper)")
    args = parser.parse_args()
    
    try:
        if args.quick:
            asyncio.run(quick_test())
        else:
            asyncio.run(test_full_pipeline())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrotto dall'utente")
    except Exception as e:
        print(f"\n\n❌ ERRORE FATALE: {e}")
        import traceback
        traceback.print_exc()
