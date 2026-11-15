"""Configuração lida de variáveis de ambiente (nada de senha no repositório)."""

import os
from pathlib import Path


def _carregar_env() -> None:
    """Lê backend/.env se existir, sem depender de biblioteca externa."""
    caminho = Path(__file__).resolve().parent.parent / ".env"
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env()

# PostgreSQL em produção/demonstração; SQLite só para rodar rápido sem Docker.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ecossistema.db")

# Validade do token de sessão, em horas.
SESSAO_HORAS = int(os.getenv("SESSAO_HORAS", "12"))

# Síntese auxiliar (opcional). Sem chave, o sistema funciona normalmente.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "15"))

# Origens liberadas para o app Flutter Web em desenvolvimento.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
