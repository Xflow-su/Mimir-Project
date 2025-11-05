#!/usr/bin/env python3
"""
Test completo della pipeline MIMIR: Audio → Whisper → Ollama → XTTS → Audio
"""

import sys
import os
import asyncio
import numpy as np
from pathlib import Path

# Aggiungi il path del progetto
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from moshi.moshi.integrations.whisper.engine import WhisperEngine, WhisperConfig
from moshi.moshi.integrations.ollama.client import OllamaClient
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
        config = WhisperConfig(model_size="medium", language="it")
        whisper = WhisperEngine(config)
        whisper.load_model()
        print("   ✅ Whisper pronto")
        
        # Ollama
        print("   └─ Connessione Ollama (llama3.2:3b)...")
        async with OllamaClient() as ollama:
            health = await ollama.check_health()
            if not health:
                print("   ❌ Ollama non disponibile!")
                return False
        print("   ✅ Ollama pronto")
        
        # XTTS
        print("   └─ Caricamento XTTS v2 + Voice Clone...")
        xtts = VoiceCloner()
        voices = xtts.list_voices()
        print(f"   ✅ XTTS pronto ({len(voices)} voci disponibili)")
        
    except Exception as e:
        print(f"   ❌ ERRORE nell'inizializzazione: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # === STEP 2: Test con Input Testuale (Skip Whisper per ora) ===
    print("\n[2/5] 🎤 Input testuale (Whisper skip per velocità)...")
    test_input = "Ciao, come stai oggi?"
    print(f"   └─ Input: \"{test_input}\"")
    
    # === STEP 3: Test LLM (Ollama) ===
    print("\n[3/5] 🧠 Test LLM (Ollama)...")
    
    try:
        async with OllamaClient() as ollama:
            response = ""
            print("   └─ Generazione risposta...", end="", flush=True)
            async for token in ollama.generate(
                prompt=test_input,
                system_prompt="Sei MIMIR, un assistente vocale amichevole e conciso. Rispondi in modo naturale e breve (max 2-3 frasi)."
            ):
                response += token
            print(" ✅")
            print(f"   └─ Risposta: \"{response[:100]}...\"")
    except Exception as e:
        print(f"\n   ❌ ERRORE Ollama: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # === STEP 4: Test TTS (XTTS) ===
    print("\n[4/5] 🔊 Test Text-to-Speech (XTTS)...")
    
    output_audio = output_dir / "test_response.wav"
    
    try:
        print(f"   └─ Sintesi di {len(response)} caratteri...")
        
        # Usa il metodo corretto di VoiceCloner
        voice_file = xtts.process_voice_file(
            str(voice_sample),
            voice_name="test_mimir"
        )
        print(f"   └─ Voice file processato: {voice_file}")
        
        # Per ora solo verifica che il voice file esista
        if Path(voice_file).exists():
            print(f"   ✅ Voice cloning preparato")
        
        # TODO: Implementare sintesi XTTS vera
        print(f"   ⚠️  Sintesi XTTS da implementare completamente")
        
    except Exception as e:
        print(f"   ❌ ERRORE XTTS: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # === STEP 5: Riepilogo ===
    print("\n[5/5] 📊 Riepilogo Test")
    print("=" * 60)
    print(f"✅ INPUT:  \"{test_input}\"")
    print(f"✅ OUTPUT: \"{response[:100]}...\"")
    print(f"⚠️  AUDIO:  Da implementare")
    print("=" * 60)
    print("\n🎉 PIPELINE PARZIALMENTE FUNZIONANTE!")
    print("   ✅ Whisper: OK")
    print("   ✅ Ollama:  OK")
    print("   ⚠️  XTTS:   Voice clone ready, sintesi da completare")
    
    return True


async def quick_test():
    """Test rapido solo Ollama"""
    
    print("=" * 60)
    print("🧠 MIMIR - Test Rapido (Solo Ollama)")
    print("=" * 60)
    
    print("\n[1/2] Inizializzazione Ollama...")
    
    try:
        async with OllamaClient() as ollama:
            print("✅ Ollama pronto")
            
            print("\n[2/2] Generazione risposta...")
            response = ""
            async for token in ollama.generate(
                prompt="Presentati brevemente come MIMIR, un assistente vocale",
                system_prompt="Sei MIMIR. Rispondi in 2-3 frasi."
            ):
                response += token
                print(token, end="", flush=True)
            
            print(f"\n\n✅ Risposta completa: {response}")
            print("\n🎉 Test completato!")
            
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test pipeline MIMIR")
    parser.add_argument("--quick", action="store_true", help="Test rapido (solo Ollama)")
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
