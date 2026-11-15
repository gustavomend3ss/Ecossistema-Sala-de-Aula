from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .database import Base, engine
from .rotas.api import router


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Ecossistema de Gestão Acadêmica — API",
    description=("Plataforma (Desenvolvimento de Sistemas Web) e assistente docente "
                 "(Inteligência Artificial) — FAINOR 2026.2. Dados fictícios."),
    version="0.2.0",
    lifespan=ciclo_de_vida,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["status"])
def status():
    return {"servico": "ecossistema-academico", "versao": app.version,
            "sintese_gemini": "ativa" if config.GEMINI_API_KEY else "desativada"}


app.include_router(router)
