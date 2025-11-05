#!/bin/bash
# Script per ricreare venv MIMIR pulito
# Esegui da: ~/mimir/

echo "🔧 MIMIR - Ricreazione Virtual Environment"
echo "=========================================="

# 1. ESCI DAL VENV (se sei dentro)
echo ""
echo "[1/6] Uscita da venv attuale..."
deactivate 2>/dev/null || echo "   (già fuori dal venv)"

# 2. ELIMINA VENV CORRENTE
echo ""
echo "[2/6] Rimozione venv corrente..."
if [ -d "venv" ]; then
    rm -rf venv
    echo "   ✅ venv/ rimosso"
else
    echo "   ⚠️  venv/ non trovato (già rimosso?)"
fi

# 3. RICREA VENV PULITO con Python 3.11
echo ""
echo "[3/6] Creazione nuovo venv (Python 3.11)..."
python3.11 -m venv venv
echo "   ✅ venv/ creato"

# 4. ATTIVA NUOVO VENV
echo ""
echo "[4/6] Attivazione nuovo venv..."
source venv/bin/activate
echo "   ✅ venv attivato"
echo "   Python: $(which python)"
echo "   Versione: $(python --version)"

# 5. AGGIORNA PIP
echo ""
echo "[5/6] Aggiornamento pip..."
pip install --upgrade pip
echo "   ✅ pip aggiornato"

# 6. INSTALLA DIPENDENZE
echo ""
echo "[6/6] Installazione dipendenze..."

# A. Dipendenze base Mimir (dalla root)
echo ""
echo "   📦 [A] Installazione requirements-mimir.txt..."
pip install -r requirements-mimir.txt
echo "   ✅ requirements-mimir.txt installato"

# B. Package moshi (editable mode)
echo ""
echo "   📦 [B] Installazione package moshi/ (editable)..."
pip install -e moshi/
echo "   ✅ moshi/ installato in modalità editable"

# VERIFICA FINALE
echo ""
echo "=========================================="
echo "✅ SETUP COMPLETATO!"
echo "=========================================="
echo ""
echo "📊 Verifica installazione:"
echo ""

# Check Python
python --version

# Check package principali
echo ""
echo "Pacchetti critici:"
pip list | grep -E "(torch|whisper|TTS|ollama|sphn|aiohttp)" || echo "⚠️  Alcuni pacchetti mancano!"

# Check import moshi
echo ""
echo "Test import moshi:"
python -c "import moshi.moshi; print(f'✅ Moshi version: {moshi.moshi.__version__}')" || echo "❌ Import moshi fallito!"

echo ""
echo "=========================================="
echo "🎯 PROSSIMI PASSI:"
echo "=========================================="
echo ""
echo "1. Verifica che Ollama sia attivo:"
echo "   ollama serve"
echo ""
echo "2. Test componenti:"
echo "   python -c \"from moshi.moshi.integrations.whisper.engine import WhisperEngine; print('✅ Whisper OK')\""
echo "   python -c \"from moshi.moshi.integrations.ollama.client import OllamaClient; print('✅ Ollama OK')\""
echo "   python -c \"from moshi.moshi.integrations.xtts.voice_cloner import VoiceCloner; print('✅ XTTS OK')\""
echo ""
echo "3. Test pipeline completo:"
echo "   python moshi/tests/test_full_pipeline.py --quick"
echo ""
echo "=========================================="
