#!/bin/bash
# Mimir Project Cleanup Script
# Rimuove file/cartelle non necessari dal fork di Moshi

set -e

echo "🧹 MIMIR PROJECT CLEANUP"
echo "========================"
echo ""

# Backup prima di tutto
BACKUP_DIR="mimir_backup_$(date +%Y%m%d_%H%M%S)"
echo "📦 Creazione backup in: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
cp -r . "$BACKUP_DIR/"
echo "✅ Backup completato"
echo ""

# ========================================
# RIMOZIONE CARTELLE GROSSE
# ========================================

echo "🗑️  Rimozione cartelle non necessarie..."

# Rust (completamente inutile per Mimir)
if [ -d "rust" ]; then
    echo "  ❌ Rimozione: rust/"
    rm -rf rust/
fi

# Client web UI (non usato)
if [ -d "client" ]; then
    echo "  ❌ Rimozione: client/"
    rm -rf client/
fi

# MLX (Apple Silicon - non supportato WSL)
if [ -d "moshi_mlx" ]; then
    echo "  ❌ Rimozione: moshi_mlx/"
    rm -rf moshi_mlx/
fi

# Test suite Moshi (non necessari)
if [ -d "moshi/tests" ]; then
    echo "  ❌ Rimozione: moshi/tests/"
    rm -rf moshi/tests/
fi

# Scripts non necessari
if [ -d "scripts" ]; then
    echo "  ❌ Rimozione: scripts/"
    rm -rf scripts/
fi

echo ""

# ========================================
# RIMOZIONE FILE SINGOLI MOSHI
# ========================================

echo "🗑️  Rimozione file Moshi non necessari..."

# Server/Client originali (sostituiti da versioni Mimir)
FILES_TO_REMOVE=(
    "moshi/moshi/server.py"
    "moshi/moshi/client.py"
    "moshi/moshi/client_gradio.py"
    "moshi/moshi/run_inference.py"
    "moshi/moshi/run_tts.py"
    "moshi/demo_moshi.ipynb"
    "moshi/Dockerfile"
)

for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        echo "  ❌ $file"
        rm "$file"
    fi
done

# Test files nei modules
find moshi/moshi/modules -name "*_test.py" -delete 2>/dev/null || true
find moshi/moshi/quantization -name "*_test.py" -delete 2>/dev/null || true

echo ""

# ========================================
# RIMOZIONE FILE DI CONFIGURAZIONE MOSHI
# ========================================

echo "🗑️  Rimozione configurazioni Moshi..."

# Manteniamo solo config/mimir/
if [ -d "config" ]; then
    find config/ -type d ! -name "mimir" ! -path "config/mimir/*" -delete 2>/dev/null || true
fi

# Docker compose (non usato)
[ -f "docker-compose.yml" ] && rm docker-compose.yml

# License Apache (per Rust)
[ -f "LICENSE-APACHE" ] && echo "  ❌ LICENSE-APACHE" && rm LICENSE-APACHE

echo ""

# ========================================
# PULIZIA FILE PYTHON CACHE
# ========================================

echo "🗑️  Pulizia cache Python..."

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

echo ""

# ========================================
# CREAZIONE .gitignore AGGIORNATO
# ========================================

echo "📝 Aggiornamento .gitignore per Mimir..."

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/

# Virtual Environment
venv/
env/
ENV/

# Mimir Specific
data/voice_models/*.wav
data/conversations/*.db
data/conversations/*.json
logs/*.log
tts-outputs/

# Models & Weights (troppo grandi)
*.safetensors
*.pth
*.ckpt

# Audio files (tranne voice sample)
*.mp3
*.ogg
*.flac

# Config with secrets
config/mimir/secrets.yaml

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Moshi files non necessari (se presenti)
rust/
client/
moshi_mlx/
scripts/
EOF

echo "✅ .gitignore aggiornato"
echo ""

# ========================================
# CREAZIONE STRUTTURA MINIMA
# ========================================

echo "📁 Verifica struttura cartelle necessarie..."

# Crea cartelle se non esistono
mkdir -p data/voice_models
mkdir -p data/conversations
mkdir -p logs
mkdir -p config/mimir

echo "✅ Struttura pronta"
echo ""

# ========================================
# REPORT FINALE
# ========================================

echo ""
echo "✅ CLEANUP COMPLETATO!"
echo "====================="
echo ""
echo "📊 Spazio liberato:"
du -sh "$BACKUP_DIR" | awk '{print "   Backup: "$1}'
du -sh . | awk '{print "   Progetto attuale: "$1}'
echo ""
echo "📁 Struttura finale:"
echo "   mimir/"
echo "   ├── config/mimir/          ← Configurazioni Mimir"
echo "   ├── data/                  ← Voce + conversazioni"
echo "   ├── moshi/moshi/"
echo "   │   ├── integrations/      ← Whisper, Ollama, XTTS"
echo "   │   ├── mimir_server.py    ← Server principale"
echo "   │   ├── mimir_client.py    ← Client CLI"
echo "   │   └── mimir_orchestrator.py"
echo "   └── requirements-mimir.txt"
echo ""
echo "💡 PROSSIMI STEP:"
echo "   1. Testa che tutto funzioni: python -m moshi.mimir_server --help"
echo "   2. Se OK, rimuovi backup: rm -rf $BACKUP_DIR"
echo "   3. Commit delle modifiche"
echo ""
echo "⚠️  NOTA: Il backup è in: $BACKUP_DIR"
echo "   Rimuovilo manualmente dopo aver verificato che tutto funzioni."
echo ""
