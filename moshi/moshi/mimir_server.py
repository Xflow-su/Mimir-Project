"""
Mimir Server - WebSocket Server per conversazione vocale real-time
Basato su architettura Moshi ma con pipeline Mimir
"""

import argparse
import asyncio
import logging
from pathlib import Path
import aiohttp
from aiohttp import web
import numpy as np
import sphn
import yaml

from .mimir_orchestrator import MimirOrchestrator, MimirConfig
from .client_utils import log

logger = logging.getLogger(__name__)


class MimirServer:
    """
    Server WebSocket per Mimir
    
    Gestisce:
    - Connessioni WebSocket client
    - Streaming audio bidirezionale
    - Pipeline Mimir completa
    """
    
    def __init__(self, config: MimirConfig, host: str = "0.0.0.0", port: int = 8998):
        self.config = config
        self.host = host
        self.port = port
        
        # Orchestrator Mimir (uno per server, condiviso tra sessioni)
        self.mimir: Optional[MimirOrchestrator] = None
        
        # Web app
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Setup routes WebSocket"""
        self.app.router.add_get("/api/chat", self.handle_chat)
        self.app.router.add_get("/health", self.handle_health)
        
        # Serve static files (web UI) se disponibili
        client_dir = Path(__file__).parent.parent.parent / "client" / "dist"
        if client_dir.exists():
            self.app.router.add_static("/", client_dir, name="static")
            logger.info(f"Serving web UI from: {client_dir}")
    
    async def handle_health(self, request):
        """Health check endpoint"""
        if self.mimir and self.mimir._initialized:
            return web.json_response({"status": "ok", "mimir": "ready"})
        return web.json_response({"status": "initializing"}, status=503)
    
    async def handle_chat(self, request):
        """
        WebSocket handler per chat vocale
        
        Protocol:
        - Client invia: [0x01][opus_audio_data]
        - Server invia: [0x01][opus_audio_data] (risposta vocale)
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        logger.info("🔗 Nuova connessione WebSocket")
        
        # Opus codec per streaming
        opus_reader = sphn.OpusStreamReader(24000)  # 24kHz
        opus_writer = sphn.OpusStreamWriter(22050)  # 22050Hz (XTTS output)
        
        # Audio buffer per accumulo
        audio_buffer = []
        buffer_duration_target = 3.0  # secondi di audio prima di processare
        
        async def send_loop():
            """Invia audio generato al client"""
            try:
                while True:
                    await asyncio.sleep(0.01)
                    
                    # Leggi audio da opus writer
                    opus_data = opus_writer.read_bytes()
                    if len(opus_data) > 0:
                        await ws.send_bytes(b"\x01" + opus_data)
                        
            except Exception as e:
                logger.error(f"Send loop error: {e}")
        
        async def recv_loop():
            """Ricevi audio dal client"""
            nonlocal audio_buffer
            
            try:
                async for message in ws:
                    if message.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {ws.exception()}")
                        break
                    elif message.type == aiohttp.WSMsgType.CLOSED:
                        logger.info("WebSocket closed by client")
                        break
                    elif message.type != aiohttp.WSMsgType.BINARY:
                        logger.warning(f"Unexpected message type: {message.type}")
                        continue
                    
                    data = message.data
                    if not isinstance(data, bytes) or len(data) == 0:
                        continue
                    
                    kind = data[0]
                    
                    if kind == 1:  # Audio data
                        payload = data[1:]
                        opus_reader.append_bytes(payload)
                        
                        # Decodifica Opus → PCM
                        pcm = opus_reader.read_pcm()
                        if len(pcm) > 0:
                            audio_buffer.append(pcm)
                            
                            # Calcola durata buffer
                            total_samples = sum(len(chunk) for chunk in audio_buffer)
                            buffer_duration = total_samples / 24000
                            
                            # Se abbiamo abbastanza audio, processa
                            if buffer_duration >= buffer_duration_target:
                                await process_audio_buffer(audio_buffer)
                                audio_buffer = []
                                
            except Exception as e:
                logger.error(f"Recv loop error: {e}")
        
        async def process_audio_buffer(buffer_chunks):
            """Processa buffer audio accumulato"""
            try:
                # Concatena tutti i chunk
                audio_full = np.concatenate(buffer_chunks)
                
                logger.info(f"Processing {len(audio_full)/24000:.2f}s audio...")
                
                # Resample 24kHz → 16kHz per Whisper
                audio_16k = resample_audio(audio_full, 24000, 16000)
                
                # Pipeline Mimir
                # 1. Whisper ASR
                user_text = await self.mimir.process_audio_chunk(audio_16k)
                
                if user_text:
                    logger.info(f"👤 User: {user_text}")
                    
                    # 2. Ollama LLM
                    response_text = await self.mimir.generate_response(user_text)
                    logger.info(f"🧙 Mimir: {response_text}")
                    
                    # 3. XTTS TTS
                    response_audio = await self.mimir.synthesize_speech(response_text)
                    
                    if response_audio is not None:
                        # Encode audio → Opus
                        # XTTS output è 22050Hz, opus_writer è configurato per questo
                        opus_writer.append_pcm(response_audio)
                        
                        logger.info(f"🔊 Audio response sent ({len(response_audio)/22050:.2f}s)")
                
            except Exception as e:
                logger.error(f"Process audio error: {e}")
        
        def resample_audio(audio, from_sr, to_sr):
            """Resample audio"""
            if from_sr == to_sr:
                return audio
            
            duration = len(audio) / from_sr
            new_length = int(duration * to_sr)
            indices = np.linspace(0, len(audio) - 1, new_length)
            return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
        
        # Start loops
        send_task = asyncio.create_task(send_loop())
        recv_task = asyncio.create_task(recv_loop())
        
        try:
            await asyncio.gather(send_task, recv_task)
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            logger.info("WebSocket disconnected")
            send_task.cancel()
            recv_task.cancel()
        
        return ws
    
    async def start(self):
        """Avvia server"""
        logger.info("🔮 Inizializzazione Mimir Server...")
        
        # Init Mimir orchestrator
        self.mimir = MimirOrchestrator(self.config)
        await self.mimir.initialize()
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"✅ Mimir Server attivo su http://{self.host}:{self.port}")
        logger.info(f"📡 WebSocket endpoint: ws://{self.host}:{self.port}/api/chat")
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutdown richiesto...")
        finally:
            await self.mimir.shutdown()
            await runner.cleanup()


# ========================================
# CLI
# ========================================

def load_config(config_file: str) -> MimirConfig:
    """Carica config da YAML"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        logger.warning(f"Config non trovato: {config_file}, uso default")
        return MimirConfig()
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    # Parse config
    config = MimirConfig()
    
    if "whisper" in data:
        config.whisper_model = data["whisper"].get("model", "medium")
        config.whisper_language = data["whisper"].get("language", "it")
        config.whisper_device = data["whisper"].get("device", "cpu")
    
    if "ollama" in data:
        config.ollama_model = data["ollama"].get("model", "llama3.2:3b")
        config.ollama_base_url = data["ollama"].get("base_url", "http://localhost:11434")
        config.ollama_temperature = data["ollama"].get("temperature", 0.75)
    
    if "xtts" in data:
        config.xtts_device = data["xtts"].get("device", "cpu")
        config.xtts_language = data["xtts"].get("language", "it")
        config.xtts_speaker_wav = data["xtts"].get("speaker_wav", "./data/voice_models/mimir_voice_fixed.wav")
        config.xtts_use_custom_voice = data["xtts"].get("use_custom_voice", True)
    
    if "personality" in data:
        config.system_prompt = data["personality"].get("system_prompt")
    
    return config


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description="Mimir Server - Voice Assistant")
    parser.add_argument("--config", type=str, default="config/mimir/settings.yaml",
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
    
    # Load config
    config = load_config(args.config)
    
    # Create server
    server = MimirServer(config, host=args.host, port=args.port)
    
    # Run
    asyncio.run(server.start())


if __name__ == "__main__":
    main()
