from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.config import settings
from app.websocket_manager import ws_manager
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/bot")
async def websocket_endpoint(websocket: WebSocket):
    try:
        logger.info("⚡ Nueva conexión WebSocket intentando conectar")
        await ws_manager.connect(websocket)
        logger.info("✅ WebSocket conectado exitosamente")
        
        while True:
            try:
                message = await websocket.receive_json()
                if message.get("type") == "warning":
                    await ws_manager.process_warning(message)
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}")
                break
                
    except Exception as e:
        logger.error(f"❌ Error en websocket_endpoint: {e}")
    finally:
        await ws_manager.disconnect(websocket)

# Incluir rutas
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 