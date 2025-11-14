# 🔮 MIMIR - Guida Installazione Completa

> Guida passo-passo per installare e configurare MIMIR su Ubuntu 24.04 LTS

---

## 📋 Prerequisiti

### Sistema Operativo
- **Ubuntu 24.04 LTS** (consigliato)
- Almeno **8GB RAM**
- **20GB spazio disco libero** (per modelli AI)
- **Connessione Internet** attiva

---

## 🚀 Installazione

### STEP 1: Preparazione Sistema

#### 1.1 Aggiorna il sistema
```bash
sudo apt update
sudo apt upgrade -y
```

#### 1.2 Installa dipendenze di sistema
```bash
# Git per clonare repository
sudo apt install -y git

# Build essentials per compilazione
sudo apt install -y build-essential

# Dipendenze audio
sudo apt install -y portaudio19-dev python3-pyaudio

# Dipendenze librosa/soundfile
sudo apt install -y libsndfile1

# FFmpeg per audio processing
sudo apt install -y ffmpeg
```

---

### STEP 2: Installazione Python 3.11.14

Ubuntu 24.04 LTS viene con Python 3.12, ma MIMIR richiede **Python 3.11.14**.

#### 2.1 Aggiungi repository Deadsnakes
```bash
sudo apt update
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
```

#### 2.2 Installa Python 3.11
```bash
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

#### 2.3 Verifica installazione
```bash
python3.11 --version
# Output atteso: Python 3.11.14
```

---

### STEP 3: Clonazione Repository

#### 3.1 Scegli directory di lavoro
```bash
# Esempio: crea cartella Projects nella home
cd ~
mkdir -p Projects
cd Projects
```

#### 3.2 Clona repository MIMIR
```bash
git clone https://github.com/TUO_USERNAME/Mimir-Project.git
cd Mimir-Project
```

> **Nota**: Sostituisci `TUO_USERNAME` con il tuo username GitHub

#### 3.3 Verifica contenuto
```bash
ls -la
# Dovresti vedere:
# - moshi/
# - config/
# - data/
# - requirements-mimir.txt
# - INSTALLAZIONE_MIMIR.md
# - CLAUDE2.md
# - README.md
```

---

### STEP 4: Configurazione Virtual Environment

#### 4.1 Crea virtual environment
```bash
python3.11 -m venv venv
```

#### 4.2 Attiva virtual environment
```bash
source venv/bin/activate
```

> **Importante**: Il prompt cambierà mostrando `(venv)` all'inizio

#### 4.3 Aggiorna pip
```bash
pip install --upgrade pip
```

#### 4.4 Installa dipendenze MIMIR
```bash
pip install -r requirements-mimir.txt
```

> **Nota**: Questo passo richiede ~10-15 minuti e scarica ~2GB di dipendenze

#### 4.5 Installa package Moshi (modalità editable)
```bash
pip install -e moshi/
```

---

### STEP 5: Installazione Ollama (LLM)

MIMIR usa Ollama per gestire il modello LLM locale.

#### 5.1 Scarica e installa Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### 5.2 Verifica installazione
```bash
ollama --version
```

#### 5.3 Scarica modello Llama3.2:3b
```bash
ollama pull llama3.2:3b
```

> **Nota**: Download ~2GB, richiede qualche minuto

#### 5.4 Avvia Ollama server
```bash
ollama serve
```

> **Importante**: Tieni questo terminale aperto! Ollama deve essere sempre attivo

**Oppure** avvia Ollama in background:
```bash
# Crea servizio systemd (opzionale)
sudo systemctl enable ollama
sudo systemctl start ollama
```

---

### STEP 6: Verifica Installazione

#### 6.1 Test import componenti
Apri un **nuovo terminale**, attiva venv e testa:

```bash
cd ~/Projects/Mimir-Project
source venv/bin/activate

# Test Whisper
python -c "from moshi.moshi.integrations.whisper.engine import WhisperEngine; print('✅ Whisper OK')"

# Test Ollama
python -c "from moshi.moshi.integrations.ollama.client import OllamaClient; print('✅ Ollama OK')"

# Test XTTS
python -c "from moshi.moshi.integrations.xtts.engine import XTTSEngine; print('✅ XTTS OK')"
```

Se tutti i test mostrano `✅`, l'installazione è corretta!

#### 6.2 Test pipeline completo
```bash
python moshi/tests/test_full_pipeline.py --quick
```

**Output atteso:**
```
============================================================
🧠 MIMIR - Test Rapido (Ollama + XTTS)
============================================================

[1/3] Inizializzazione...
✅ Componenti pronti

[2/3] Generazione risposta LLM...
✅ Risposta: Sono Mimir, l'antica figura della mitologia norrena...

[3/3] Sintesi vocale...
✅ Audio: .../data/test_outputs/test_quick.wav

🎉 Test completato!
```

---

## 🎮 Utilizzo Base

### Avvio Server MIMIR

#### Terminale 1: Ollama (se non in background)
```bash
ollama serve
```

#### Terminale 2: Server MIMIR
```bash
cd ~/Projects/Mimir-Project
source venv/bin/activate
python -m moshi.moshi.mimir_server
```

**Output atteso:**
```
============================================================
🔮 MIMIR Server Attivo
============================================================
📡 URL:     http://0.0.0.0:8998
🔌 WebSocket: ws://0.0.0.0:8998/api/chat
❤️  Health:  http://0.0.0.0:8998/health
============================================================
```

### Test Server

#### Opzione 1: Browser
Apri browser e vai a: `http://localhost:8998`

#### Opzione 2: Test script
In un **terzo terminale**:
```bash
cd ~/Projects/Mimir-Project
source venv/bin/activate
python moshi/tests/test_server.py
```

---

## 🔧 Comandi Git Utili

### Aggiornare repository locale
```bash
# Salva modifiche locali (se presenti)
git stash

# Scarica ultimi aggiornamenti
git pull origin main

# Ripristina modifiche locali
git stash pop
```

### Verificare stato repository
```bash
git status
```

### Vedere modifiche
```bash
git log --oneline -10
```

### Creare un branch per esperimenti
```bash
git checkout -b mio-esperimento
```

### Tornare al branch main
```bash
git checkout main
```

---

## 📁 Struttura Progetto

```
Mimir-Project/
├── moshi/                          # Core engine
│   ├── moshi/
│   │   ├── integrations/          # Integrazioni (Whisper, Ollama, XTTS)
│   │   ├── models/                # Modelli base Moshi
│   │   ├── mimir_server.py        # Server WebSocket
│   │   └── mimir_orchestrator.py  # Orchestratore pipeline
│   └── tests/                     # Test automatizzati
│
├── config/                         # Configurazioni
│   └── mimir/
│       └── mimir_server.yaml      # Config server principale
│
├── data/                           # Dati e modelli
│   ├── voice_models/              # Modelli voce
│   │   └── voce_mimir/
│   │       └── mimir_voice_master.wav  # Voce clonata
│   └── test_outputs/              # Output test
│
├── logs/                           # Log runtime
│
├── venv/                           # Virtual environment (gitignored)
│
├── requirements-mimir.txt          # Dipendenze Python
├── INSTALLAZIONE_MIMIR.md         # Questa guida
├── CLAUDE2.md                      # Documentazione tecnica
└── README.md                       # Overview progetto
```

---

## 🐛 Troubleshooting

### Problema: `ModuleNotFoundError: No module named 'moshi'`
**Soluzione:**
```bash
source venv/bin/activate
pip install -e moshi/
```

### Problema: Ollama non si connette
**Verifica che Ollama sia attivo:**
```bash
curl http://localhost:11434/api/tags
```

**Riavvia Ollama:**
```bash
pkill ollama
ollama serve
```

### Problema: Audio non funziona
**Installa dipendenze audio:**
```bash
sudo apt install -y portaudio19-dev python3-pyaudio libsndfile1
pip install --force-reinstall sounddevice soundfile
```

### Problema: XTTS errore memoria
**Ridurre qualità sintesi in `config/mimir/mimir_server.yaml`:**
```yaml
xtts:
  device: "cpu"
  temperature: 0.65  # Ridotto per più stabilità
```

### Problema: Git pull fallisce con conflitti
**Reset al commit remoto (ATTENZIONE: perde modifiche locali):**
```bash
git fetch origin
git reset --hard origin/main
```

**Oppure salva modifiche prima:**
```bash
git stash
git pull origin main
git stash pop
```

---

## 📊 Configurazione Avanzata

### Modifica Personalità MIMIR

Edita: `config/mimir/mimir_server.yaml`

```yaml
personality:
  name: "Mimir"
  system_prompt: |
    Sei Mimir, custode della saggezza norrena.
    # Modifica questo prompt per cambiare personalità
```

Poi riavvia server.

### Cambiare Modello LLM

```bash
# Scarica altro modello
ollama pull llama3.2:1b  # Più veloce, meno accurato
# oppure
ollama pull llama3.2:7b  # Più lento, più accurato

# Modifica config
nano config/mimir/mimir_server.yaml
# Cambia: ollama.model: "llama3.2:1b"
```

---

## 🎯 Prossimi Passi

Dopo aver completato l'installazione:

1. **Test completo pipeline**
   ```bash
   python moshi/tests/test_full_pipeline.py
   ```

2. **Avvia server e prova conversazione**
   ```bash
   python -m moshi.moshi.mimir_server
   ```

3. **Leggi documentazione tecnica**: `CLAUDE2.md`

4. **Esplora codice integrazioni**: `moshi/moshi/integrations/`

---

## 📝 Note Importanti

- **Virtual environment**: Ricorda SEMPRE di attivare venv con `source venv/bin/activate`
- **Ollama server**: Deve essere sempre attivo durante l'uso di MIMIR
- **Modelli AI**: I modelli vengono scaricati automaticamente al primo uso (~4GB totali)
- **Privacy**: Tutto funziona **100% offline**, nessuna chiamata cloud

---

## 🆘 Supporto

- **Bug o problemi**: Apri issue su GitHub
- **Domande**: Consulta `CLAUDE2.md` per dettagli tecnici
- **Logs**: Controlla `logs/mimir_server.log` per debug

---

## ✅ Checklist Installazione

- [ ] Ubuntu 24.04 LTS installato
- [ ] Python 3.11.14 installato e verificato
- [ ] Repository clonata
- [ ] Virtual environment creato e attivato
- [ ] Dipendenze installate (`requirements-mimir.txt`)
- [ ] Package moshi installato (`pip install -e moshi/`)
- [ ] Ollama installato e modello scaricato
- [ ] Test import passati (Whisper, Ollama, XTTS)
- [ ] Test pipeline rapido completato
- [ ] Server MIMIR avviato con successo

---

**Versione**: 1.0  
**Data**: 2025-01-14  
**Compatibile con**: Ubuntu 24.04 LTS, Python 3.11.14, Moshi v0.2.12a3
