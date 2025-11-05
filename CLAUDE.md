# 📘 CLAUDE.md — Knowledge Base per il Progetto MIMIR

> File di contesto per Claude / LLM da leggere prima di ogni assistenza o aggiornamento tecnico.
> Contiene la struttura completa, lo stato dei componenti, le configurazioni attuali e le prossime attività.

---

## 🧠 PANORAMICA PROGETTO

**Nome:** MIMIR  
**Tipo:** Assistente vocale locale / framework AI multimodale  
**Architettura:** Python + Ollama (LLM) + Whisper (ASR) + XTTS (TTS)  
**Modalità:** Tutto in locale (no cloud / no API esterne)

**Obiettivo:**  
Creare un assistente vocale personale completamente offline, con pipeline locale end-to-end:
- Input vocale → Trascrizione Whisper
- Testo → Risposta LLM (Ollama)
- Output → Sintesi XTTS (voce clonata)
- In futuro → UI grafica / Web UI leggera / memoria persistente / hardware (es. Raspberry Pi)

---

## ⚙️ AMBIENTE DI SVILUPPO

| Componente | Versione / Note |
|-------------|-----------------|
| **Sistema** | WSL Ubuntu su Windows |
| **Python** | 3.11.14 (virtualenv `venv`) |
| **LLM** | Ollama + `llama3.2:3b` |
| **ASR (Speech-to-Text)** | Whisper Medium |
| **TTS (Text-to-Speech)** | XTTS v2 + Voice Clone locale |
| **Server WebSocket** | `mimir_server.py` su porta `8998` |
| **Client CLI** | `mimir_client.py` |
| **Config attiva** | `config/mimir/mimir_server.yaml` |
| **Dipendenze** | `requirements-mimir.txt` |
| **Stato** | Tutti i test principali ✅ passati |

---

## 📂 STRUTTURA ATTUALE DEL PROGETTO

mimir/
├── CONTRIBUTING.md
├── FAQ.md
├── LICENSE-MIT
├── MIMIR_PROJECT_STRUCTURE.md
├── README.md
│
├── 📁 config/
│ └── mimir/
│ └── mimir_server.yaml # Config principale
│
├── 📁 data/
│ ├── conversations/ # Memoria futura (dialoghi salvati)
│ └── voice_models/
│ └── voce_mimir/
│ ├── mimir_voice_fixed.wav
│ ├── mimir_voice_master.wav
│
├── 📁 moshi/ # Fork adattato da Kyutai (core engine)
│ ├── LICENSE
│ ├── README.md
│ ├── pyproject.toml
│ ├── setup.cfg
│ ├── requirements.txt
│ ├── moshi/
│ │ ├── init.py # version = "0.2.12a3"
│ │ ├── mimir_server.py # Server principale (porta 8998)
│ │ ├── mimir_client.py # Client CLI
│ │ ├── mimir_orchestrator.py # Pipeline LLM+ASR+TTS
│ │ ├── integrations/
│ │ │ ├── ollama/ # Integrazione LLM locale
│ │ │ ├── whisper/ # Speech-to-Text
│ │ │ └── xtts/ # Text-to-Speech + Voice Clone
│ │ ├── conditioners/ # Struttura base Kyutai
│ │ ├── models/ # Loader e modelli Torch
│ │ ├── modules/ # Componenti audio (resample, conv, gating, ecc.)
│ │ ├── quantization/ # Compressione e quantizzazione
│ │ └── utils/ # Utility varie
│ └── moshi.egg-info/
│
├── 📁 logs/ # (Vuota - destinata ai log runtime)
│
└── 📄 requirements-mimir.txt # Dipendenze attuali


---

## 🧩 STATO COMPONENTI

| Componente | Stato | Note |
|-------------|--------|------|
| **Server** (`mimir_server.py`) | ✅ OK | Funziona su `localhost:8998`, risponde con `404: Not Found` |
| **Client CLI** | ✅ OK | `--help` e connessione testati |
| **Ollama** | ✅ OK | Connessione locale confermata |
| **Whisper** | ✅ OK | Inizializzazione completata |
| **XTTS v2** | ✅ OK | Voice clone caricato (3 voci trovate) |
| **Voice Clone** | ✅ OK | File audio 46min valido e usato |
| **Config YAML** | ✅ OK | Lettura riuscita, fallback se mancante |
| **Import __version__** | ⚠️ Avviso ignorabile | `from moshi.moshi import __version__` funziona |

---

## 🧪 TEST ESEGUITI

| Test | Esito | Comando |
|------|--------|---------|
| Server Dry Run | ✅ | `python -m moshi.moshi.mimir_server --debug --host localhost --port 8998` |
| Ollama Connectivity | ✅ | Script Python con `test_ollama_connection()` |
| Voice Cloner | ✅ | Script Python `VoiceCloner().list_voices()` |
| Config / Versione | ✅ | `python -c "import moshi.moshi; print(moshi.moshi.__version__)"` |

---

## 🛠️ PROBLEMI NOTI

| Tipo | Descrizione | Gravità |
|------|--------------|---------|
| ImportError `__version__` | Solo se importato come `from moshi import __version__` | 🟢 Ignorabile |
| Mancanza `settings.yaml` | Warning automatico, fallback a default | 🟢 Ignorabile |
| Audio output su WSL | Funziona solo in modalità test / no-mic | 🟡 Limitato |
| Caricamento XTTS lento | Normale (1–2GB modelli Torch) | 🟢 OK |

---

## 🎯 PROSSIMI STEP

| Step | Descrizione | Priorità |
|------|--------------|----------|
| 🧩 Test end-to-end | Eseguire conversazione da client CLI verso server | 🔥 Alta |
| 💾 Aggiungere memoria locale | Implementare `SQLite` per log conversazioni | 🟠 Media |
| 🖥️ Interfaccia UI | In futuro: CLI evoluta o Web UI leggera (locale) | 🟠 Media |
| 🧠 Ottimizzazione modelli | Possibile riduzione peso XTTS / Whisper | 🔵 Facoltativo |
| 🔌 Hardware Integration | In futuro: Raspberry Pi + LED emozionali | 🔵 Futuro |

---

## 🔐 PRIVACY E MODALITÀ

- Tutto il sistema funziona **100% offline**
- Nessuna chiamata esterna o cloud
- Ollama, Whisper e XTTS girano **in locale**
- Tutti i dati vocali restano su disco (`data/`)

---

## 📄 STORICO VERSIONI

| Versione | Data | Descrizione |
|-----------|------|-------------|
| 0.1 | 2025-10 | Setup base e integrazione Kyutai |
| 0.2 | 2025-11 | Server attivo, XTTS + Ollama + Whisper funzionanti |
| 0.2.12a3 | Attuale | Versione rilevata da `__init__.py` |

---

## 📚 NOTE FINALI

Claude deve sempre:
1. **Leggere questo file (`CLAUDE.md`) prima di qualsiasi task**
2. **Fare riferimento ai path e nomi file esatti**
3. **Non creare file o cartelle fuori dallo schema indicato**
4. **Usare `python -m moshi.moshi.<modulo>` per avviare i componenti**
5. **Tenersi coerente con la versione `0.2.12a3` del core Moshi**

---

_Questo file sarà aggiornato man mano con nuovi componenti, versioni e piani di sviluppo._
