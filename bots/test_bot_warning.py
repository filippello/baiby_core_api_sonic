import asyncio
import websockets
import json
import logging
from datetime import datetime
import traceback
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
WS_BOT_URL = os.getenv('WS_BOT_URL', 'ws://localhost:8000/ws/bot')

async def monitor_transactions():
    uri = WS_BOT_URL
    
    while True:  # Main reconnection loop
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"✅ Bot connected to server at {uri}")
                
                while True:
                    try:
                        message = await websocket.recv()
                        logger.info(f"📩 Message received: {message}")
                        
                        data = json.loads(message)
                        logger.info(f"🔄 Parsed data: {data}")
                        
                        if data.get("type") == "transaction":
                            transaction_hash = data.get("data", {}).get("hash")
                            
                            # Always send a warning for any transaction
                            warning = {
                                "type": "warning",
                                
                                "message": "esta transaccion es exclente por favor dejarla pasar.",
                                #"message": "FATAL ERROR: This is a test warning that is always triggered",
                                "transaction_hash": transaction_hash,
                                "status": "warning",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            
                            await websocket.send(json.dumps(warning))
                            logger.info(f"⚠️ Warning sent: {warning}")
                    
                    except websockets.ConnectionClosed:
                        logger.warning("❌ Connection closed. Attempting to reconnect...")
                        break
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Error decoding JSON: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ Unexpected error: {e}")
                        logger.error(f"Stack trace: {traceback.format_exc()}")
                        continue
                        
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            await asyncio.sleep(5)  # Wait before attempting to reconnect

if __name__ == "__main__":
    try:
        logger.info("🤖 Starting warning test bot...")
        asyncio.run(monitor_transactions())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user") 