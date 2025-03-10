import asyncio
import websockets
import json
import logging
from datetime import datetime
import traceback
from multiversx_sdk import ProxyNetworkProvider, Address
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración desde variables de entorno
PROVIDER_URL = "https://testnet-gateway.multiversx.com"
WS_BOT_URL = os.getenv('WS_BOT_URL', 'ws://localhost:8000/ws/bot')

# Inicializar el provider de MultiversX
provider = ProxyNetworkProvider(PROVIDER_URL)

async def get_egld_balance(address_str: str) -> float:
    try:
        logger.info(f"🔍 Intentando obtener balance para {address_str}")
        address = Address.from_bech32(address_str)
        account = provider.get_account(address)
        balance = float(account.balance) / (10**18)  # Convertir de denominación más pequeña a EGLD
        logger.info(f"💰 Balance EGLD obtenido para {address_str}: {balance}")
        return balance
    except Exception as e:
        logger.error(f"❌ Error obteniendo balance: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return 0

async def monitor_transactions():
    uri = WS_BOT_URL
    
    while True:  # Bucle principal para reconexión
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"✅ Bot conectado al servidor en {uri}")
                
                while True:
                    try:
                        message = await websocket.recv()
                        logger.info(f"📩 Mensaje recibido: {message}")
                        
                        data = json.loads(message)
                        logger.info(f"🔄 Datos parseados: {data}")
                        
                        if data.get("type") == "transaction":
                            transactions = data.get("data", {}).get("transactions", [])
                            transaction_hash = data.get("data", {}).get("hash")
                            safewallet = data.get("data", {}).get("safewallet")
                            
                            logger.info(f"🔍 Analizando transacción para safewallet: {safewallet}")
                            
                            if not safewallet:
                                logger.warning("⚠️ No se encontró safewallet en el mensaje")
                                continue
                            
                            # Obtener balance EGLD
                            current_balance = await get_egld_balance(safewallet)
                            logger.info(f"💰 Balance actual en EGLD: {current_balance}")
                            
                            # Analizar transacciones
                            for tx in transactions:
                                value = float(tx.get("value", "0")) / (10**18)  # Convertir a EGLD
                                if value > current_balance * 0.9:  # Si la transacción usa más del 90% del balance
                                    warning = {
                                        "type": "warning",
                                        "message": f"Potential wallet draining attempt! Attempting to send {value} EGLD from a wallet with {current_balance} EGLD balance",
                                        "transaction_hash": transaction_hash,
                                        "status": "warning",
                                        "timestamp": datetime.utcnow().isoformat()
                                    }
                                    await websocket.send(json.dumps(warning))
                                    logger.info(f"⚠️ Warning enviado: {warning}")
                    
                    except websockets.ConnectionClosed:
                        logger.warning("❌ Conexión cerrada. Intentando reconectar...")
                        break
                        
        except Exception as e:
            logger.error(f"❌ Error en la conexión: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            await asyncio.sleep(5)  # Esperar antes de intentar reconectar

if __name__ == "__main__":
    asyncio.run(monitor_transactions()) 