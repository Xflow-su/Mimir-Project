"""
Mimir Server - WebSocket Server per conversazione vocale real-time
Integra: Whisper (ASR) → Ollama (LLM) → XTTS (TTS)
"""

import argparse
import asyncio
import logging
from pathlib import Path
import aiohttp
from aiohttp import web
import numpy as np
import yaml
import traceback

# Import integrations
from moshi.moshi.integrations.whisper.engine import WhisperEngine, WhisperConfig
from moshi.moshi.integrations.ollama.client import OllamaClient
from moshi.moshi.integrations.xtts.engine import XTTSEngine, XTTSConfig

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


class MimirServer:
    """
    Server WebSocket per conversazioni vocali con MIMIR
    
    Pipeline:
    1. Client invia audio → Whisper (ASR)
    2. Testo → Ollama (LLM)
    3. Risposta → XTTS (TTS)
    4. Audio → Client
    """
    
    def __init__(self, config_path: str = None, host: str = "0.0.0.0", port: int = 8998):
        self.host = host
        self.port = port
        self.config = self._load_config(config_path)
        
        # Componenti pipeline
        self.whisper: WhisperEngine = None
        self.ollama: OllamaClient = None
        self.xtts: XTTSEngine = None
        
        # Web app
        self.app = web.Application()
        self.setup_routes()
        
        # Stats
        self.active_connections = 0
        self.total_requests = 0
        
    def _load_config(self, config_path: str = None) -> dict:
        """Carica configurazione da YAML"""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        
        # Config default - FIX: Path assoluto CORRETTO
        logger.warning("Config non trovato, uso default")
        
        # FIX: Trova root correttamente
        # __file__ è in: moshi/moshi/mimir_server.py
        # Quindi: parent.parent.parent = root progetto
        project_root = Path(__file__).resolve().parent.parent.parent
        
        # Prova vari path possibili
        possible_paths = [
            project_root / "data" / "voice_models" / "voce_mimir" / "mimir_voice_master.wav",
            Path(__file__).resolve().parent.parent.parent / "data" / "voice_models" / "voce_mimir" / "mimir_voice_master.wav",
            Path.cwd() / "data" / "voice_models" / "voce_mimir" / "mimir_voice_master.wav"
        ]

        
        speaker_wav = None
        for path in possible_paths:
            logger.debug(f"Provo path: {path}")
            if path.exists():
                speaker_wav = path
                logger.info(f"✅ Speaker WAV trovato: {speaker_wav}")
                break
        
        if not speaker_wav:
            logger.error("❌ NESSUN file speaker_wav trovato!")
            logger.error(f"   Root progetto: {project_root}")
            logger.error(f"   Provati: {[str(p) for p in possible_paths]}")
            # Lista file disponibili
            voice_dir = project_root / "data" / "voice_models"
            if voice_dir.exists():
                logger.info(f"   File disponibili in {voice_dir}:")
                for f in voice_dir.rglob("*.wav"):
                    logger.info(f"     - {f}")
        
        return {
            "whisper": {"model": "medium", "language": "it", "device": "cpu"},
            "ollama": {"model": "llama3.2:3b", "base_url": "http://localhost:11434"},
            "xtts": {
                "device": "cpu",
                "language": "it",
                "speaker_wav": str(speaker_wav) if speaker_wav else None,
                "use_custom_voice": speaker_wav is not None
            },
            "personality": {
                "system_prompt": "Sei MIMIR, un assistente vocale saggio e conciso. Rispondi in modo naturale e breve (max 2-3 frasi)."
            }
        }
    async def initialize(self):
        """Inizializza tutti i componenti della pipeline"""
        logger.info("🔮 Inizializzazione MIMIR Server...")
        
        # 1. Whisper ASR
        logger.info("  📝 Caricamento Whisper...")
        whisper_config = WhisperConfig(
            model_size=self.config["whisper"]["model"],
            language=self.config["whisper"]["language"],
            device=self.config["whisper"]["device"]
        )
        self.whisper = WhisperEngine(whisper_config)
        self.whisper.load_model()
        logger.info("  ✅ Whisper pronto")
        
        # 2. Ollama LLM
        logger.info("  🧠 Connessione Ollama...")
        # OllamaClient usa context manager, lo inizializzeremo per richiesta
        logger.info("  ✅ Ollama configurato")
        
        # 3. XTTS TTS
        logger.info("  🔊 Caricamento XTTS...")
        
        project_root = Path(__file__).resolve().parent.parent.parent
        xtts_config = XTTSConfig(
            device=self.config["xtts"]["device"],
            language=self.config["xtts"]["language"],
            speaker_wav=str(project_root / "data" / "voice_models" / "voce_mimir" / "mimir_voice_master.wav"),
            use_custom_voice=True
        )
        self.xtts = XTTSEngine(xtts_config)
        self.xtts.load_model()
        logger.info("  ✅ XTTS pronto")
        
        logger.info("✅ MIMIR Server pronto!")
    
    def setup_routes(self):
        """Setup route WebSocket"""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_get("/api/chat", self.handle_chat)
        self.app.router.add_get("/stats", self.handle_stats)
    
    async def handle_index(self, request):
        """Pagina index"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MIMIR Server</title>
            <style>
                body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
                h1 { color: #2c3e50; }
                .status { padding: 10px; background: #27ae60; color: white; border-radius: 5px; }
                .endpoint { background: #ecf0f1; padding: 10px; margin: 10px 0; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>🔮 MIMIR Server</h1>
            <div class="status">✅ Server Attivo</div>
            <h2>Endpoints Disponibili:</h2>
            <div class="endpoint"><b>GET /health</b> - Health check</div>
            <div class="endpoint"><b>GET /stats</b> - Server statistics</div>
            <div class="endpoint"><b>WS /api/chat</b> - WebSocket per conversazioni vocali</div>
            <h2>Status:</h2>
            <p>Connessioni attive: <b id="connections">0</b></p>
            <p>Richieste totali: <b id="requests">0</b></p>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")
    
    async def handle_health(self, request):
        """Health check endpoint"""
        health = {
            "status": "ok",
            "components": {
                "whisper": self.whisper is not None,
                "xtts": self.xtts is not None,
                "ollama": True  # Configurato
            },
            "active_connections": self.active_connections
        }
        return web.json_response(health)
    
    async def handle_stats(self, request):
        """Statistics endpoint"""
        stats = {
            "active_connections": self.active_connections,
            "total_requests": self.total_requests,
            "whisper_stats": self.whisper.get_stats() if self.whisper else {},
            "xtts_stats": self.xtts.get_stats() if self.xtts else {}
        }
        return web.json_response(stats)
    
    async def handle_chat(self, request):
        """
        WebSocket handler per conversazioni vocali
        
        Protocol:
        - Client → Server: JSON {"type": "text", "data": "..."}
        - Server → Client: JSON {"type": "text"|"audio", "data": "..."}
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.active_connections += 1
        logger.info(f"🔗 Nuova connessione WebSocket (totale: {self.active_connections})")
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._process_message(ws, msg.data)
            
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    data = msg.data
                    kind = data[0] if len(data) > 0 else None
            
                    if kind == 1:
                        audio_data = data[1:]
                        logger.info(f"🎧 Audio ricevuto: {len(audio_data)} bytes")
                        # TODO: qui puoi passare l'audio a Whisper o salvarlo su file
                        # esempio temporaneo:
                        # with open("received_audio.opus", "ab") as f:
                        #     f.write(audio_data)
                    else:
                        logger.warning(f"Tipo messaggio sconosciuto: {kind}")
            
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")

        except Exception as e:
            logger.error(f"Errore gestione WebSocket: {e}")
            
        finally:
            self.active_connections -= 1
            logger.info(f"❌ Connessione chiusa (attive: {self.active_connections})")
        
        return ws
    
    async def _process_message(self, ws: web.WebSocketResponse, message: str):
        """Processa messaggio dal client"""
        try:
            import json
            data = json.loads(message)
            msg_type = data.get("type")
            content = data.get("data")
            
            if msg_type == "text":
                # Input testuale diretto
                await self._handle_text_input(ws, content)
            
            elif msg_type == "ping":
                # Ping/pong per keep-alive
                await ws.send_json({"type": "pong", "data": "ok"})
            
            else:
                logger.warning(f"Tipo messaggio sconosciuto: {msg_type}")
                
        except json.JSONDecodeError:
            logger.error("Messaggio JSON malformato")
        except Exception as e:
            logger.error(f"Errore processing: {e}")
            await ws.send_json({"type": "error", "data": str(e)})
    
    async def _handle_text_input(self, ws: web.WebSocketResponse, user_text: str):
        """
        Gestisce input testuale:
        1. Testo → Ollama (LLM)
        2. Risposta → XTTS (TTS)
        3. Audio → Client
        """
        self.total_requests += 1
        logger.info(f"👤 Input: {user_text}")
        
        # Invia ACK
        await ws.send_json({"type": "ack", "data": "Processing..."})
        
        try:
            # 1. Genera risposta con Ollama
            response_text = ""
            async with OllamaClient() as ollama:
                await ws.send_json({"type": "status", "data": "Thinking..."})
                
                async for token in ollama.generate(
                    prompt=user_text,
                    system_prompt=self.config["personality"]["system_prompt"]
                ):
                    response_text += token
            
            logger.info(f"🧙 Risposta: {response_text[:100]}...")
            
            # Invia risposta testuale
            await ws.send_json({"type": "text", "data": response_text})
            
            # 2. Sintetizza audio con XTTS
            await ws.send_json({"type": "status", "data": "Generating audio..."})
            
            audio = await self.xtts.synthesize(response_text)
            
            if audio is not None:
                # Converti audio in base64 per invio
                import base64
                audio_bytes = (audio * 32767).astype(np.int16).tobytes()
                audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                
                await ws.send_json({
                    "type": "audio",
                    "data": audio_b64,
                    "sample_rate": self.xtts.config.sample_rate
                })
                
                logger.info("✅ Audio inviato al client")
            else:
                logger.warning("⚠️ Sintesi audio fallita")
            
        except Exception as e:
            logger.error(f"Errore pipeline: {e}")
            await ws.send_json({"type": "error", "data": str(e)})
    
    async def start(self):
        """Avvia il server"""
        await self.initialize()
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"🔮 MIMIR Server Attivo")
        logger.info(f"{'='*60}")
        logger.info(f"📡 URL:     http://{self.host}:{self.port}")
        logger.info(f"🔌 WebSocket: ws://{self.host}:{self.port}/api/chat")
        logger.info(f"❤️  Health:  http://{self.host}:{self.port}/health")
        logger.info(f"📊 Stats:   http://{self.host}:{self.port}/stats")
        logger.info(f"{'='*60}")
        logger.info(f"Premi Ctrl+C per fermare il server")
        logger.info(f"")
        
        # Keep running
        try:
            stop_event = asyncio.Event()
            
            def signal_handler():
                logger.info("\n🛑 Shutdown richiesto...")
                stop_event.set()
            
            # Registra handler per Ctrl+C
            import signal
            loop = asyncio.get_event_loop()
            loop.add_signal_handler(signal.SIGINT, signal_handler)
            
            # Attendi stop
            await stop_event.wait()
            
        except Exception as e:
            logger.error(f"Errore: {e}")
            traceback.print_exc()
        finally:
            await runner.cleanup()
            logger.info("✅ Server chiuso")


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description="MIMIR Server - Voice Assistant")
    parser.add_argument("--config", type=str, default="config/mimir/mimir_server.yaml",
                       help="Path al file configurazione")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                       help="Host server")
    parser.add_argument("--port", type=int, default=8998,
                       help="Porta server")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create e avvia server
    server = MimirServer(config_path=args.config, host=args.host, port=args.port)
    
    # Run
    asyncio.run(server.start())


if __name__ == "__main__":
    main()
