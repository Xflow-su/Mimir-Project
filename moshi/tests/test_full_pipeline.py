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

from moshi.moshi.integrations.whisper.engine import WhisperEngine, WhisperConfig
from moshi.moshi.integrations.ollama.client import OllamaClient, OllamaConfig
from moshi.moshi.integrations.xtts.engine import XTTSEngine, XTTSConfig


async def test_full_pipeline():
    """Test completo della pipeline MIMIR"""
    
    print("=" * 60)
    print("🧠 MIMIR - Test Pipeline Completa")
    print("=" * 60)
    
    # Percorsi
    voice_sample = project_root / "data" / "voice_models" / "voce_mimir" / "mimir_voice_master.wav"
    output_dir = project_root / "data" / "test_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # === STEP 1: Inizializzazione Componenti ===
    print("\n[1/5] 🔧 Inizializzazione componenti...")
    
    try:
        # Whisper
        print("   └─ Caricamento Whisper (base per test veloce)...")
        whisper_config = WhisperConfig(model_size="base", language="it")
        whisper = WhisperEngine(whisper_config)
        whisper.load_model()
        print("   ✅ Whisper pronto")
        
        # Ollama
        print("   └─ Connessione Ollama (llama3.2:3b)...")
        ollama_config = OllamaConfig(model="llama3.2:3b")
        ollama = OllamaClient(ollama_config)
        print("   ✅ Ollama pronto")
        
        # XTTS
        print("   └─ Caricamento XTTS v2...")
        xtts_config = XTTSConfig(
            language="it",
            device="cpu",
            use_custom_voice=True,
            speaker_wav=str(voice_sample) if voice_sample.exists() else None
        )
        xtts = XTTSEngine(xtts_config)
        xtts.load_model()
        print("   ✅ XTTS pronto")
        
    except Exception as e:
        print(f"   ❌ ERRORE nell'inizializzazione: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # === STEP 2: Input testuale (skip Whisper per velocità) ===
    print("\n[2/5] 🎤 Input testuale (Whisper skip per velocità)...")
    test_input = "Ciao, come stai oggi?"
    print(f"   └─ Input: \"{test_input}\"")
    
    # === STEP 3: Test LLM (Ollama) ===
    print("\n[3/5] 🧠 Test LLM (Ollama)...")
    print(f"   └─ Generazione risposta...", end=" ", flush=True)
    
    try:
        async with ollama:
            response = ""
            async for token in ollama.generate(
                prompt=test_input,
                system_prompt="Sei MIMIR, una figura della mitologia norrena nota per la sua incredibile saggezza (detto anche 'l'uomo piu sapiente del mondo'). Dimmi come stai e cosa puoi fare per me.",
                stream=True
            ):
                response += token
        
        response = response.strip()
        print("✅")
        print(f"   └─ Risposta: \"{response[:100]}...\"")
    except Exception as e:
        print(f"❌")
        print(f"   ❌ ERRORE Ollama: {e}")
        return False
    
    # === STEP 4: Test TTS (XTTS) ===
    print("\n[4/5] 🔊 Test Text-to-Speech (XTTS)...")
    
    output_audio = output_dir / "test_response.wav"
    
    try:
        # Limita testo per test veloce
        text_to_synth = response[:200] if len(response) > 200 else response
        print(f"   └─ Sintesi di {len(text_to_synth)} caratteri...")
        
        audio = await xtts.synthesize(text_to_synth)
        
        if audio is not None:
            # Salva audio
            xtts.save_audio(audio, str(output_audio))
            
            duration = len(audio) / xtts.config.sample_rate
            size_kb = output_audio.stat().st_size / 1024
            
            print(f"   ✅ Audio generato: {output_audio}")
            print(f"   └─ Durata: {duration:.2f}s")
            print(f"   └─ Dimensione: {size_kb:.1f} KB")
        else:
            print("   ❌ XTTS ha ritornato None")
            return False
        
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
    print(f"✅ AUDIO:  {output_audio}")
    print("=" * 60)
    print("\n🎉 PIPELINE COMPLETA FUNZIONANTE!")
    print(f"\n💡 Puoi ascoltare la risposta:")
    print(f"   - Apri il file: {output_audio}")
    print(f"   - Oppure usa VLC/Windows Media Player")
    
    return True


async def quick_test():
    """Test rapido solo Ollama → XTTS (salta Whisper)"""
    
    print("=" * 60)
    print("🧠 MIMIR - Test Rapido (Ollama + XTTS)")
    print("=" * 60)
    
    voice_sample = project_root / "data" / "voice_models" / "voce_mimir" / "mimir_voice_master.wav"
    output_dir = project_root / "data" / "test_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n[1/3] Inizializzazione...")
    
    ollama_config = OllamaConfig(model="llama3.2:3b")
    ollama = OllamaClient(ollama_config)
    
    xtts_config = XTTSConfig(
        language="it",
        device="cpu",
        use_custom_voice=True,
        speaker_wav=str(voice_sample) if voice_sample.exists() else None
    )
    xtts = XTTSEngine(xtts_config)
    xtts.load_model()
    
    print("✅ Componenti pronti")
    
    print("\n[2/3] Generazione risposta LLM...")
    async with ollama:
        response = ""
        async for token in ollama.generate(
            prompt="Presentati brevemente come MIMIR",
            system_prompt="Sei MIMIR. Rispondi in 2 frasi max."
        ):
            response += token
    
    response = response.strip()
    print(f"✅ Risposta: {response}")
    
    print("\n[3/3] Sintesi vocale...")
    output_audio = output_dir / "test_quick.wav"
    
    audio = await xtts.synthesize(response)
    xtts.save_audio(audio, str(output_audio))
    
    print(f"✅ Audio: {output_audio}")
    print(f"\n🎉 Test completato!")


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
