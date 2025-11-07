"""
Test del server MIMIR via WebSocket
"""

import asyncio
import json
import aiohttp


async def test_websocket_connection():
    """Test connessione WebSocket"""
    print("=" * 60)
    print("🧪 Test MIMIR Server WebSocket")
    print("=" * 60)
    
    url = "ws://localhost:8998/api/chat"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(url) as ws:
                print("\n✅ Connesso al server!")
                
                # Test 1: Ping
                print("\n[Test 1] Ping/Pong...")
                await ws.send_json({"type": "ping", "data": "test"})
                response = await ws.receive_json()
                print(f"  ✅ Pong ricevuto: {response}")
                
                # Test 2: Messaggio testuale
                print("\n[Test 2] Invio messaggio testuale...")
                test_message = "Ciao MIMIR, presentati brevemente"
                await ws.send_json({"type": "text", "data": test_message})
                print(f"  📤 Inviato: {test_message}")
                
                # Ricevi risposte
                print("\n[Test 3] Ricezione risposte...")
                timeout = 60  # 60 secondi timeout
                
                async with asyncio.timeout(timeout):
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            msg_type = data.get("type")
                            content = data.get("data")
                            
                            if msg_type == "ack":
                                print(f"  🔄 ACK: {content}")
                                
                            elif msg_type == "status":
                                print(f"  ⏳ Status: {content}")
                                
                            elif msg_type == "text":
                                print(f"  ✅ Risposta: {content[:100]}...")
                                
                            elif msg_type == "audio":
                                print(f"  🔊 Audio ricevuto ({len(content)} bytes)")
                                # Audio completo ricevuto, esci
                                break
                                
                            elif msg_type == "error":
                                print(f"  ❌ Errore: {content}")
                                break
                                
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"  ❌ WebSocket error")
                            break
                
                print("\n✅ Test completato!")
                
        except asyncio.TimeoutError:
            print("\n⏱️ Timeout - server troppo lento")
        except Exception as e:
            print(f"\n❌ Errore: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("\n⚠️  Assicurati che il server sia avviato:")
    print("   python -m moshi.moshi.mimir_server\n")
    
    try:
        asyncio.run(test_websocket_connection())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrotto")
