"""
Mimir Client CLI
Client command-line per conversazione vocale con Mimir server
"""

import argparse
import asyncio
import logging
import queue
import sys
from typing import Optional

import aiohttp
import numpy as np
import sounddevice as sd
import sphn

logger = logging.getLogger(__name__)


class MimirClient:
    """
    Client CLI per Mimir Server
    
    Gestisce:
    - Registrazione audio da microfono
    - Invio audio via WebSocket
    - Ricezione e playback risposta
    """
    
    def __init__(
        self,
        server_url: str = "ws://localhost:8998/api/chat",
        sample_rate: int = 24000,
        frame_size: int = 1920
    ):
        self.server_url = server_url
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self._done = False
        
        # Audio streams
        self._in_stream: Optional[sd.InputStream] = None
        self._out_stream: Optional[sd.OutputStream] = None
        
        # Opus codecs
        self._opus_writer = sphn.OpusStreamWriter(sample_rate)
        self._opus_reader = sphn.OpusStreamReader(sample_rate)
        
        # Output queue
        self._output_queue = queue.Queue()
        
        # State
        self._is_recording = False
        self._is_speaking = False
        
    def _on_audio_input(self, indata, frames, time_info, status):
        """Callback microfono"""
        if status:
            logger.warning(f"Input status: {status}")
        
        if self._is_recording and not self._is_speaking:
            # Converti a float32 mono
            audio = indata[:, 0].astype(np.float32)
            self._opus_writer.append_pcm(audio)
    
    def _on_audio_output(self, outdata, frames, time_info, status):
        """Callback speaker"""
        if status:
            logger.warning(f"Output status: {status}")
        
        try:
            # Prendi audio dalla queue
            data = self._output_queue.get_nowait()
            outdata[:] = data.reshape(-1, 1)
        except queue.Empty:
            # Silenzio se niente in queue
            outdata.fill(0)
    
    async def _queue_loop(self):
        """Loop invio audio al server"""
        while not self._done:
            await asyncio.sleep(0.001)
            
            # Leggi audio encodato da opus
            msg = self._opus_writer.read_bytes()
            if len(msg) > 0:
                try:
                    await self.websocket.send_bytes(b"\x01" + msg)
                except Exception as e:
                    logger.error(f"Send error: {e}")
                    self._done = True
                    return
    
    async def _decoder_loop(self):
        """Loop decodifica audio dal server"""
        all_pcm_data = None
        
        while not self._done:
            await asyncio.sleep(0.001)
            
            # Decodifica opus → PCM
            pcm = self._opus_reader.read_pcm()
            
            if len(pcm) > 0:
                self._is_speaking = True
                
                if all_pcm_data is None:
                    all_pcm_data = pcm
                else:
                    all_pcm_data = np.concatenate((all_pcm_data, pcm))
                
                # Metti in queue chunk per playback
                while len(all_pcm_data) >= self.frame_size:
                    chunk = all_pcm_data[:self.frame_size]
                    self._output_queue.put(chunk)
                    all_pcm_data = all_pcm_data[self.frame_size:]
            else:
                # Nessun audio in arrivo
                if self._is_speaking and self._output_queue.qsize() == 0:
                    self._is_speaking = False
    
    async def _recv_loop(self):
        """Loop ricezione messaggi dal server"""
        try:
            async for message in self.websocket:
                if message.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("Server closed connection")
                    break
                elif message.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self.websocket.exception()}")
                    break
                elif message.type != aiohttp.WSMsgType.BINARY:
                    logger.warning(f"Unexpected message type: {message.type}")
                    continue
                
                data = message.data
                if not isinstance(data, bytes) or len(data) == 0:
                    continue
                
                kind = data[0]
                
                if kind == 1:  # Audio response
                    payload = data[1:]
                    self._opus_reader.append_bytes(payload)
                    
        except Exception as e:
            logger.error(f"Recv loop error: {e}")
        finally:
            self._done = True
    
    async def start(self):
        """Avvia client e connetti al server"""
        logger.info(f"🔗 Connessione a {self.server_url}...")
        
        # Connetti WebSocket
        session = aiohttp.ClientSession()
        try:
            self.websocket = await session.ws_connect(self.server_url)
            logger.info("✅ Connesso!")
        except Exception as e:
            logger.error(f"❌ Connessione fallita: {e}")
            await session.close()
            return
        
        # Avvia audio streams
        try:
            self._in_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.frame_size,
                callback=self._on_audio_input
            )
            
            self._out_stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.frame_size,
                callback=self._on_audio_output
            )
            
            self._in_stream.start()
            self._out_stream.start()
            
        except Exception as e:
            logger.error(f"Audio stream error: {e}")
            return
        
        # Start loops
        self._is_recording = True
        
        tasks = [
            asyncio.create_task(self._queue_loop()),
            asyncio.create_task(self._decoder_loop()),
            asyncio.create_task(self._recv_loop())
        ]
        
        # User interface loop
        print("\n" + "="*60)
        print("🔮 Mimir Client Attivo")
        print("="*60)
        print("\nComandi:")
        print("  - Parla normalmente nel microfono")
        print("  - Premi Ctrl+C per uscire")
        print("\n💡 Tip: Parla per 2-3 secondi, poi attendi risposta")
        print("="*60 + "\n")
        
        try:
            # Attendi interruzione utente
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n\n🛑 Disconnessione...")
        finally:
            self._done = True
            self._is_recording = False
            
            # Stop audio
            if self._in_stream:
                self._in_stream.stop()
                self._in_stream.close()
            if self._out_stream:
                self._out_stream.stop()
                self._out_stream.close()
            
            # Cancel tasks
            for task in tasks:
                task.cancel()
            
            # Close websocket
            await self.websocket.close()
            await session.close()
            
            print("✅ Disconnesso")


# ========================================
# TEST MODE - Senza Microfono
# ========================================

class MimirTestClient:
    """
    Client di test che simula conversazione senza microfono
    Utile per test server senza hardware audio
    """
    
    def __init__(self, server_url: str = "ws://localhost:8998/api/chat"):
        self.server_url = server_url
    
    async def test_conversation(self):
        """Simula conversazione di test"""
        print("=== Mimir Test Client ===\n")
        print(f"Connessione a {self.server_url}...\n")
        
        session = aiohttp.ClientSession()
        
        try:
            ws = await session.ws_connect(self.server_url)
            print("✅ Connesso!\n")
            
            # Simula invio audio (silenzio)
            opus_writer = sphn.OpusStreamWriter(24000)
            
            # Genera 3 secondi di silenzio (per trigger server)
            silence = np.zeros(3 * 24000, dtype=np.float32)
            opus_writer.append_pcm(silence)
            
            audio_data = opus_writer.read_bytes()
            await ws.send_bytes(b"\x01" + audio_data)
            
            print("📤 Audio test inviato")
            print("⏳ Attendo risposta...\n")
            
            # Ricevi risposta
            timeout = 30  # secondi
            try:
                async with asyncio.timeout(timeout):
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            print("✅ Risposta ricevuta dal server!")
                            print(f"   Dati: {len(msg.data)} bytes\n")
                            break
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            print("❌ Server chiuso connessione")
                            break
                            
            except asyncio.TimeoutError:
                print("⏱️ Timeout - nessuna risposta")
            
            await ws.close()
            
        except Exception as e:
            print(f"❌ Errore: {e}")
        finally:
            await session.close()
        
        print("\n✅ Test completato")


# ========================================
# CLI
# ========================================

def main():
    parser = argparse.ArgumentParser(description="Mimir Client - Voice Assistant Client")
    parser.add_argument("--url", type=str, default="ws://localhost:8998/api/chat",
                       help="WebSocket URL del server")
    parser.add_argument("--test", action="store_true",
                       help="Test mode (senza microfono)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if args.test:
        # Test mode
        client = MimirTestClient(args.url)
        asyncio.run(client.test_conversation())
    else:
        # Normal mode con microfono
        client = MimirClient(args.url)
        asyncio.run(client.start())


if __name__ == "__main__":
    main()
