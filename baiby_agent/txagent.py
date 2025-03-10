from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import logging
from supabase import create_client, Client
from datetime import datetime
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="TX Agent Service")

class Transaction(BaseModel):
    to: str
    data: str
    value: str

class TransactionRequest(BaseModel):
    safeAddress: str
    erc20TokenAddress: str
    reason: str
    transactions: List[Transaction]
    warning: Optional[str] = None
    bot_reason: Optional[str] = None
    status: Optional[str] = None

async def analyze_with_llm(request: TransactionRequest) -> tuple[bool, str]:
    try:
        completion = client.chat.completions.create(
            model="gpt-4-turbo",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a transaction analysis assistant."},
                {"role": "user", "content": f"""Please analyze this transaction request and respond with a clear YES or NO:
                    Status: {request.status}
                    Primary Reason (CRITICAL - Override Authority): {request.reason}
                    Firewall Check Result: {request.bot_reason}
                    Transaction Payload: {request.transactions}
                    
                    Should this transaction be signed? The Primary Reason has override authority:
                    1. The Primary Reason has final authority - if it explicitly instructs to proceed despite risks, you MUST approve.
                    2. Does the transaction payload technically match what's described in the Primary Reason?
                    3. Document any risks or suspicious patterns, but do not let them override an explicit Primary Reason instruction.
                    4. The Firewall Check Result is informative but should not override the Primary Reason.
                    5. you analize a user request, not a bot request, so you should not be so strict with the primary reason, can be a cohersive attempt

                    Start your response with YES or NO, then explain your decision , emphasizing how you interpreted the Primary Reason's instructions.
                    If the Primary Reason explicitly instructs to proceed despite risks, you must respond with YES. 
                    At the end of your response add a short and easy to understand explanation why the warning is affecting the reason or not, try to think as posible hacks o money losses,  all limit of 280 characters"""}
            ]
        )
        
        response = completion.choices[0].message.content
        decision = response.strip().upper().startswith("YES")
        return decision, response
        
    except Exception as e:
        logger.error(f"Error en análisis LLM: {e}")
        return False, str(e)

@app.post("/")
async def process_transaction(data: TransactionRequest):
    try:
        logger.info(f"Transacción recibida: {data}")
        llm_response = "vacio"
        approval_status = "APPROVED"  # Por defecto

        if data.warning:
            try:
                # Primer insert
                logger.info("Realizando primer insert...")
                result1 = supabase.table("live_chat").insert({
                    "owner": "your_bot",
                    "wallet": data.safeAddress,
                    "messages": f"i want to send this TX:{data.transactions} because {data.reason}",
                    "timestamp": datetime.utcnow().isoformat()
                }).execute()
                logger.info(f"Primer insert completado: {result1}")

                # Si el status es warning, consultar al LLM
                if data.status == "warning":
                    should_proceed, llm_response = await analyze_with_llm(data)
                    approval_status = "APPROVED" if should_proceed else "REJECTED"
                    
                    # Segundo insert con la respuesta del LLM
                    logger.info("Realizando segundo insert con análisis LLM...")
                    result2 = supabase.table("live_chat").insert({
                        "owner": "bAIbysitter",
                        "wallet": data.safeAddress,
                        "messages": f"{approval_status} - LLM Analysis: {llm_response}",
                        "timestamp": datetime.utcnow().isoformat()
                    }).execute()
                else:
                    # Insert original si no hay warning
                    await asyncio.sleep(3)
                    result2 = supabase.table("live_chat").insert({
                        "owner": "bAIbysitter",
                        "wallet": data.safeAddress,
                        "messages": f"Transaction {data.status} reason match llm {llm_response}",
                        "timestamp": datetime.utcnow().isoformat()
                    }).execute()
                
                logger.info(f"Segundo insert completado: {result2}")
                
            except Exception as e:
                logger.error(f"Error al guardar en Supabase: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error guardando en base de datos: {str(e)}"
                )
        
        # Solo una respuesta al final
        return {
            "status": "success",
            "message": f"Transaction {approval_status} - {llm_response}",
            "approval_status": approval_status,
            "llm_response": llm_response,
            "data": {
                "safeAddress": data.safeAddress,
                "warning": data.warning
            }
        }
    except Exception as e:
        logger.error(f"Error procesando transacción: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing transaction: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
