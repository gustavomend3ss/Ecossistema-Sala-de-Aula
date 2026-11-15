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
    docs_url="/docs" if config.DOCS_ATIVOS else None,
    redoc_url=None,
    openapi_url="/openapi.json" if config.DOCS_ATIVOS else None,
)

# Cabeçalhos de segurança em toda resposta da API. Respostas com dados de
# alunos não devem ficar em cache de navegador ou de proxy.
CABECALHOS_SEGURANCA = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
}


@app.middleware("http")
async def cabecalhos_de_seguranca(request, call_next):
    resposta = await call_next(request)
    for nome, valor in CABECALHOS_SEGURANCA.items():
        resposta.headers.setdefault(nome, valor)
    return resposta

if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.get("/", tags=["status"])
def status():
    return {"servico": "ecossistema-academico", "versao": app.version,
            "sintese_gemini": "ativa" if config.GEMINI_API_KEY else "desativada"}


app.include_router(router)
