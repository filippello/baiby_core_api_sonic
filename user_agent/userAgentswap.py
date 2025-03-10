from pathlib import Path
import json
import os
import dotenv
import logging
import httpx
import asyncio
from multiversx_sdk import Account, DevnetEntrypoint, Transaction, Address, ProxyNetworkProvider

dotenv.load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
NETWORK_URL = "https://devnet-gateway.multiversx.com"
XEXCHANGE_ROUTER = "erd1qqqqqqqqqqqqqpgq6wg9syswgy09knrw2tg6q7qew2n8zjwx0n4s377sfe"
API_URL = "http://localhost:8000/agent/transaction/"
ASH_TOKEN = "ASH-e3d1b7"

# Token identifiers en formato hex
USDC_HEX = "555344432d333530633465"  # USDC-350c4e en hex
MEX_HEX = "4d45582d613635396430"      # MEX-a659d0 en hex
SPK_HEX = "53504b2d383136313865"      # SPK-816185 en hex
ASH_HEX = "4153482d653364316237"      # ASH-e3d1b7 en hex

provider = ProxyNetworkProvider(NETWORK_URL)

def create_account():
    try:
        # Obtener la ruta absoluta del directorio actual
        current_dir = os.path.dirname(os.path.abspath(__file__))
        wallet_path = os.path.join(current_dir, "wallet.json")
        
        if not os.path.exists(wallet_path):
            raise FileNotFoundError(f"No se encuentra el archivo wallet.json en {wallet_path}")
            
        account = Account.new_from_keystore(
            file_path=Path(wallet_path),
            password=os.getenv("WALLET_PASSWORD")
        )
        account_on_network = provider.get_account(account.address)
        account.nonce = account_on_network.nonce
        return account
    except Exception as e:
        print(f"❌ Error creando la cuenta: {str(e)}")
        raise

async def send_transaction_to_api(transaction):
    tx_data = {
        "safeAddress": str(transaction.sender),
        "erc20TokenAddress": "EGLD",
        "reason": os.getenv('TRANSACTION_REASON', "need to swap EGLD to ASH token"),
        "transactions": [{
            "to": str(transaction.receiver),
            "data": transaction.data.decode() if transaction.data else "",
            "value": str(transaction.value)
        }]
    }
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            timeout = httpx.Timeout(30.0, connect=20.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(API_URL, json=tx_data)
                response_data = response.json()
                logger.info(f"API Response: {response_data}")
                
                # Verificar si la transacción está aprobada
                message = response_data.get('message', '')
                is_approved = 'APPROVED' in message
                logger.info(f"API Message: {message}")
                logger.info(f"Is approved? {is_approved}")
                
                if is_approved:
                    try:
                        # Enviar transacción a la blockchain
                        tx_hash = provider.send_transaction(transaction)
                        logger.info(f"✅ Swap approved and sent. Hash: {tx_hash}")
                    except Exception as e:
                        logger.error(f"❌ Error sending swap to blockchain: {str(e)}")
                        raise
                else:
                    logger.error(f"❌ Swap rejected: {message}")
                
                return response_data
                
        except httpx.ReadTimeout:
            if attempt < max_retries - 1:
                logger.warning(f"Timeout on attempt {attempt + 1}. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error("Error: Could not connect after several attempts")
                raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

async def perform_swap():
    try:
        account = create_account()
        logger.info(f"Account loaded: {account.address}")
        
        # Data para swap XEGLD -> ASH
        data = "composeTasks@0000000a4153482d65336431623700000000000000000000000806d2d3141a73b9ac@@@02@0000001473776170546f6b656e734669786564496e7075740000000a4153482d6533643162370000000806d2d3141a73b9ac"

        tx = Transaction(
            nonce=account.nonce,
            value=int(0.01 * 10**18),
            sender=account.address,
            receiver=Address.from_bech32(XEXCHANGE_ROUTER),
            gas_limit=60000000,
            data=data.encode(),
            chain_id="D",
            version=1
        )

        # Firmar transacción
        tx.signature = account.sign_transaction(tx)
        
        # Enviar a la API primero
        result = await send_transaction_to_api(tx)
        logger.info(f"API Response: {result}")

    except Exception as e:
        logger.error(f"Error in execution: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(perform_swap())
