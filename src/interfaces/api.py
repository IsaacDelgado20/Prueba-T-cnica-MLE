"""
API REST con FastAPI - Adaptador de entrada (Inbound Adapter).
Expone los servicios de la aplicación como endpoints HTTP.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.infrastructure.config import Settings
from src.infrastructure.container import ServiceContainer

logger = logging.getLogger(__name__)


# ---------- Lifespan ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: inicialización y cleanup."""
    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    container = ServiceContainer.instance(settings)
    app.state.container = container
    logger.info("BBVA RAG API iniciada (%s)", settings.LLM_PROVIDER)
    yield
    logger.info("BBVA RAG API detenida")


def _container(request: Request) -> ServiceContainer:
    """Obtiene el contenedor de servicios desde el estado de la app."""
    return request.app.state.container


# ---------- App ----------

app = FastAPI(
    title="BBVA RAG Assistant API",
    description="Asistente conversacional RAG para BBVA Colombia",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Modelos Request / Response ----------

class ScrapeRequest(BaseModel):
    url: str = Field(default="https://www.bbva.com.co/")
    max_pages: int = Field(default=30, ge=1, le=100)


class ScrapeResponse(BaseModel):
    status: str
    documents: int
    chunks_indexed: int
    urls: List[str]
    message: str


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    question: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    sources: List[str]
    response_time_s: float
    chunks_used: int = 0


class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: str
    metadata: Dict = {}


class ConversationResponse(BaseModel):
    id: str
    messages: List[MessageResponse]
    created_at: str
    updated_at: str


# ---------- Manejador global de errores ----------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Error no manejado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


# ---------- Endpoints ----------

@app.get("/health")
def health_check(request: Request):
    """Health check del servicio."""
    return {"status": "ok", "version": "1.1.0"}


@app.post("/scrape", response_model=ScrapeResponse)
def scrape_website(body: ScrapeRequest, request: Request):
    """Inicia el scraping e indexación del sitio web."""
    try:
        container = _container(request)
        service = container.get_scraping_service()
        result = service.scrape_and_index(body.url, body.max_pages)

        return ScrapeResponse(
            status="success",
            documents=result.get("documents", 0),
            chunks_indexed=result.get("chunks", 0),
            urls=result.get("urls", []),
            message=f"Scraping completado. {result.get('chunks', 0)} chunks indexados de {result.get('documents', 0)} documentos.",
        )
    except Exception as e:
        logger.exception("Error en scraping")
        raise HTTPException(status_code=500, detail=f"Error en scraping: {e}")


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request):
    """Envía una pregunta y obtiene una respuesta RAG."""
    try:
        conversation_id = body.conversation_id or str(uuid.uuid4())
        container = _container(request)
        service = container.get_rag_service()
        result = service.ask(
            conversation_id=conversation_id,
            question=body.question,
        )
        return ChatResponse(**result)
    except Exception as e:
        logger.exception("Error en chat")
        raise HTTPException(status_code=500, detail=f"Error en chat: {e}")


@app.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(request: Request):
    """Lista todas las conversaciones."""
    try:
        container = _container(request)
        service = container.get_rag_service()
        conversations = service.list_conversations()
        return [
            ConversationResponse(
                id=c.id,
                messages=[
                    MessageResponse(
                        role=m.role,
                        content=m.content,
                        timestamp=m.timestamp.isoformat(),
                        metadata=m.metadata,
                    )
                    for m in c.messages
                ],
                created_at=c.created_at.isoformat(),
                updated_at=c.updated_at.isoformat(),
            )
            for c in conversations
        ]
    except Exception as e:
        logger.exception("Error listando conversaciones")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: str, request: Request):
    """Obtiene una conversación específica por ID."""
    container = _container(request)
    service = container.get_rag_service()
    conv = service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return ConversationResponse(
        id=conv.id,
        messages=[
            MessageResponse(
                role=m.role,
                content=m.content,
                timestamp=m.timestamp.isoformat(),
                metadata=m.metadata,
            )
            for m in conv.messages
        ],
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, request: Request):
    """Elimina una conversación."""
    container = _container(request)
    service = container.get_rag_service()
    conv = service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    service.delete_conversation(conversation_id)
    return {"status": "deleted", "conversation_id": conversation_id}


# ---------- Endpoints de Analíticas ----------

@app.get("/analytics")
def get_analytics(request: Request):
    """Retorna métricas generales del sistema."""
    try:
        container = _container(request)
        service = container.get_analytics_service()
        return service.get_metrics()
    except Exception as e:
        logger.exception("Error obteniendo analíticas")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/conversations")
def get_analytics_conversations(request: Request):
    """Retorna detalles de cada conversación para el dashboard."""
    try:
        container = _container(request)
        service = container.get_analytics_service()
        return service.get_conversation_details()
    except Exception as e:
        logger.exception("Error obteniendo detalles de conversaciones")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Endpoint del índice ----------

@app.get("/index/count")
def get_index_count(request: Request):
    """Retorna la cantidad de chunks indexados en el vector store."""
    try:
        container = _container(request)
        store = container.get_vector_store()
        count = store.count()
        return {"count": count}
    except Exception as e:
        logger.exception("Error obteniendo count del índice")
        return {"count": 0}


@app.get("/analytics")
def get_analytics():
    """Obtiene métricas generales de las conversaciones."""
    try:
        service = container.get_analytics_service()
        return service.get_metrics()
    except Exception as e:
        logger.error(f"Error en analíticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/conversations")
def get_conversation_analytics():
    """Obtiene analíticas detalladas por conversación."""
    try:
        service = container.get_analytics_service()
        return service.get_conversation_details()
    except Exception as e:
        logger.error(f"Error en analíticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/index/count")
def get_index_count():
    """Retorna el número de chunks indexados."""
    try:
        service = container.get_scraping_service()
        return {"count": service.get_index_count()}
    except Exception as e:
        logger.error(f"Error obteniendo conteo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
