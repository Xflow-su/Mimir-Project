# 🔮 MIMIR - Struttura Progetto Finale

## 📁 Tree Completo (post-cleanup)

```
mimir/
│
├── 📄 README.md                          # Documentazione principale Mimir
├── 📄 requirements-mimir.txt              # Dipendenze Python
├── 📄 .gitignore                          # Ignore aggiornato
│
├── 📁 config/
│   └── mimir/
│       ├── mimir_server.yaml              # Config server principale
│       └── secrets.yaml                   # (gitignored) API keys, etc.
│
├── 📁 data/
│   ├── voice_models/
│   │   ├── mimir_voice_1hour.wav          # Voce clonata (gitignored)
│   │   └── README.md                      # Istruzioni voice cloning
│   └── conversations/
│       ├── .gitkeep
│       └── *.db                           # (futuro) Database memoria
│
├── 📁 logs/
│   ├── .gitkeep
│   └── mimir_server.log                   # (gitignored) Log runtime
│
├── 📁 moshi/                              # Directory principale
│   ├── 📄 pyproject.toml                  # Metadati pacchetto Python
│   ├── 📄 requirements.txt                # Dipendenze base Moshi
│   ├── 📄 setup.cfg                       # Configurazione linting
│   │
│   └── moshi/                             # Pacchetto Python
│       ├── __init__.py                    # v0.2.12a3
│       │
│       ├── 🔥 mimir_server.py             # ← SERVER PRINCIPALE MIMIR
│       ├── 🔥 mimir_client.py             # ← CLIENT CLI MIMIR
│       ├── 🔥 mimir_orchestrator.py       # ← PIPELINE ORCHESTRATOR
│       │
│       ├── client_utils.py                # Utility console/logging
│       │
│       ├── 📁 integrations/               # ← INTEGRAZIONI CUSTOM MIMIR
│       │   ├── __init__.py
│       │   │
│       │   ├── whisper/                   # ASR (Speech-to-Text)
│       │   │   ├── __init__.py
│       │   │   ├── engine.py              # Whisper engine core
│       │   │   └── adapter.py             # Adapter per Mimi audio
│       │   │
│       │   ├── ollama/                    # LLM locale
│       │   │   ├── __init__.py
│       │   │   ├── client.py              # Client Ollama REST API
│       │   │   └── adapter.py             # Adapter LMGen-compatible
│       │   │
│       │   └── xtts/                      # TTS (Text-to-Speech)
│       │       ├── __init__.py
│       │       ├── engine.py              # XTTS v2 engine
│       │       ├── voice_cloner.py        # Voice cloning utility
│       │       └── adapter.py             # Adapter per Mimi audio
│       │
│       ├── 📁 models/                     # Core models (da Moshi)
│       │   ├── __init__.py
│       │   ├── lm.py                      # LMModel, LMGen (base classes)
│       │   ├── lm_utils.py
│       │   └── loaders.py                 # Model loading utilities
│       │
│       ├── 📁 modules/                    # Building blocks (da Moshi)
│       │   ├── __init__.py
│       │   ├── conv.py                    # Convolution layers
│       │   ├── streaming.py               # Streaming utilities
│       │   ├── transformer.py             # Transformer core
│       │   └── rope.py                    # Rotary embeddings
│       │
│       └── 📁 utils/                      # Utility generiche
│           ├── __init__.py
│           └── compile.py                 # Torch compile utilities
│
└── 📁 docs/                               # (opzionale) Documentazione extra
    ├── SETUP.md
    ├── VOICE_CLONING.md
    └── API.md
```

---

## 🎯 File Critici per Mimir

### **Server Core (3 files)**
```
moshi/moshi/mimir_server.py         → WebSocket server
moshi/moshi/mimir_client.py         → CLI client
moshi/moshi/mimir_orchestrator.py   → Pipeline: Whisper→Ollama→XTTS
```

### **Integrazioni (9 files)**
```
moshi/moshi/integrations/whisper/engine.py      → Whisper ASR
moshi/moshi/integrations/whisper/adapter.py     → Whisper→Mimi adapter

moshi/moshi/integrations/ollama/client.py       → Ollama REST client
moshi/moshi/integrations/ollama/adapter.py      → Ollama→LMGen adapter

moshi/moshi/integrations/xtts/engine.py         → XTTS TTS engine
moshi/moshi/integrations/xtts/adapter.py        → XTTS→Mimi adapter
moshi/moshi/integrations/xtts/voice_cloner.py   → Voice cloning tools
```

### **Configurazione (2 files)**
```
config/mimir/mimir_server.yaml      → Configurazione completa
requirements-mimir.txt              → Dipendenze Python
```

---

## ❌ File/Cartelle RIMOSSI (dopo cleanup)

### **Cartelle grosse (~500MB+)**
- ❌ `rust/` - Backend Rust (non usato)
- ❌ `client/` - Web UI (non usato)
- ❌ `moshi_mlx/` - Apple MLX backend (non supportato WSL)
- ❌ `scripts/` - Script di esempio Moshi

### **File Moshi originali sostituiti**
- ❌ `moshi/moshi/server.py` → sostituito da `mimir_server.py`
- ❌ `moshi/moshi/client.py` → sostituito da `mimir_client.py`
- ❌ `moshi/moshi/run_inference.py`
- ❌ `moshi/moshi/run_tts.py`
- ❌ `moshi/moshi/client_gradio.py`

### **Test e demo**
- ❌ `moshi/tests/`
- ❌ `moshi/demo_moshi.ipynb`
- ❌ `moshi/moshi/modules/*_test.py`

### **Build/CI**
- ❌ `moshi/Dockerfile`
- ❌ `.github/` (se presente)
- ❌ `docker-compose.yml`

---

## 📊 Stima Dimensioni

**Prima del cleanup:**
- Totale: ~800-1000 MB
- Rust binaries: ~300 MB
- Node modules (client): ~150 MB
- MLX: ~100 MB
- Tests/scripts: ~50 MB

**Dopo il cleanup:**
- Core Mimir: ~100-150 MB
- Dipendenze Python: ~500 MB (venv)
- **Totale progetto: ~200 MB** ✅

---

## 🚀 Come Usare lo Script di Cleanup

```bash
# 1. Backup automatico
cd ~/mimir
chmod +x cleanup_mimir_project.sh
./cleanup_mimir_project.sh

# 2. Verifica che tutto funzioni
python -m moshi.mimir_server --help
python -m moshi.mimir_client --help

# 3. Test import integrazioni
python -c "from moshi.integrations.whisper import WhisperEngine; print('✅ Whisper OK')"
python -c "from moshi.integrations.ollama import OllamaClient; print('✅ Ollama OK')"
python -c "from moshi.integrations.xtts import XTTSEngine; print('✅ XTTS OK')"

# 4. Se tutto OK, rimuovi backup
rm -rf mimir_backup_*

# 5. Commit
git add .
git commit -m "feat: cleanup progetto - rimossi file Moshi non necessari"
```

---

## 🔧 Dipendenze Post-Cleanup

### **Python Packages (requirements-mimir.txt)**
```
# Core Moshi (minimo necessario)
torch==2.2.0
numpy==1.26.4
aiohttp>=3.10.5
sphn==0.1.4

# Mimir Integrations
openai-whisper==20231117    # ASR
ollama==0.1.6               # LLM
TTS==0.22.0                 # XTTS v2

# Utilities
pyyaml==6.0.1
sounddevice==0.5.0
```

### **Servizi Esterni Locali**
- Ollama server: `ollama serve` (porta 11434)
- Nessun altro servizio richiesto ✅

---

## 💡 Vantaggi Post-Cleanup

1. **Dimensione ridotta**: 800MB → 200MB (-75%)
2. **Codice più chiaro**: Solo file Mimir-specific
3. **Installazione veloce**: Meno dipendenze
4. **Git più leggero**: Clone/push/pull rapidi
5. **Focus**: Solo ciò che serve a Mimir

---

## 🎯 Prossimi Step (Dopo Cleanup)

1. ✅ Cleanup completato
2. ⏳ Fix import relativi (prossimo task)
3. ⏳ Test pipeline end-to-end
4. ⏳ Setup voice cloning
5. ⏳ Deploy su Raspberry Pi 5

---

## 📝 Note Importanti

- **Backup**: Lo script crea automaticamente `mimir_backup_YYYYMMDD_HHMMSS/`
- **Reversibilità**: Puoi sempre ripristinare dal backup
- **Git safe**: Tutti i file rimossi sono già nel .gitignore
- **Dipendenze**: Manteniamo solo il minimo indispensabile da Moshi

---

**Versione**: 1.0  
**Ultimo aggiornamento**: 2025-11-03  
**Compatibile con**: Moshi v0.2.12a3
