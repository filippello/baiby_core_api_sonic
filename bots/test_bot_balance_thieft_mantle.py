import asyncio
import websockets
import json
import logging
from datetime import datetime
import traceback
from dotenv import load_dotenv
import os
from multiversx_sdk_network_providers import ProxyNetworkProvider
from multiversx_sdk_core import Address

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
WS_BOT_URL = os.getenv('WS_BOT_URL', 'ws://localhost:8000/ws/bot')
provider = ProxyNetworkProvider("https://devnet-gateway.multiversx.com")
DRAIN_THRESHOLD = 0.9  # 90% of balance

def parse_value(value_str):
    try:
        clean_value = value_str.split('.')[0]
        return int(clean_value)
    except Exception as e:
        logger.error(f"Error parsing value {value_str}: {e}")
        return 0

async def monitor_transactions():
    uri = WS_BOT_URL
    
    while True:
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
                            transactions = data.get("data", {}).get("transactions", [])
                            transaction_hash = data.get("data", {}).get("hash")
                            safe_wallet = data.get("data", {}).get("safewallet")
                            
                            if safe_wallet:
                                # Get wallet balance
                                account = provider.get_account(Address.from_bech32(safe_wallet))
                                wallet_balance = int(account.balance)
                                
                                for tx in transactions:
                                    value = parse_value(tx.get("value", "0"))
                                    
                                    # Calculate percentage of balance being transferred
                                    if wallet_balance > 0:
                                        transfer_percentage = value / wallet_balance
                                        
                                        if transfer_percentage >= DRAIN_THRESHOLD:
                                            warning = {
                                                "type": "warning",
                                                "message": f"⚠️ WALLET DRAIN DETECTED: Attempting to transfer {transfer_percentage*100:.2f}% of wallet balance ({value} of {wallet_balance} wei)",
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
            logger.info("🔄 Attempting to reconnect in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        logger.info("🤖 Starting balance theft detection bot...")
        asyncio.run(monitor_transactions())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")