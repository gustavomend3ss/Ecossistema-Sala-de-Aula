"""Configuração lida de variáveis de ambiente (nada de senha no repositório)."""

import os
import secrets
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

# Na Vercel (serviço "api"), o único lugar gravável é /tmp. Sem DATABASE_URL,
# o banco é um SQLite ali, recriado com os dados fictícios quando a função
# esfria. Para dados persistentes, defina DATABASE_URL com um PostgreSQL.
NA_VERCEL = bool(os.getenv("VERCEL"))

# PostgreSQL em produção/demonstração; SQLite só para rodar rápido sem Docker.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:////tmp/ecossistema.db" if NA_VERCEL else "sqlite:///./ecossistema.db",
)

# Chave que assina os tokens de acesso. Em produção, defina SECRET_KEY no
# ambiente (na Vercel: Settings > Environment Variables). A chave fixa abaixo
# está no repositório público, então só vale fora da Vercel, em
# desenvolvimento. Na Vercel sem SECRET_KEY, cada instância sorteia a sua: os
# tokens antigos deixam de valer quando a instância reinicia, o que combina com
# o SQLite em /tmp, que também é recriado nessa hora.
CHAVE_DE_DESENVOLVIMENTO = "ecossistema-academico-chave-de-desenvolvimento"
SECRET_KEY = os.getenv("SECRET_KEY") or (
    secrets.token_urlsafe(32) if NA_VERCEL else CHAVE_DE_DESENVOLVIMENTO)

# Recria os dados fictícios quando o banco está vazio (usado na Vercel, onde o
# SQLite fica em /tmp e some quando a função esfria).
SEMEAR_SE_VAZIO = os.getenv("SEMEAR_SE_VAZIO", "1" if NA_VERCEL else "0") == "1"

# Validade do token de sessão, em horas.
SESSAO_HORAS = int(os.getenv("SESSAO_HORAS", "12"))

# Síntese auxiliar (opcional). Sem chave, o sistema funciona normalmente.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "15"))

# Origens liberadas para chamar a API de outro endereço (Flutter em
# desenvolvimento). Na Vercel, app e API ficam no mesmo domínio, então nenhuma
# origem externa é liberada, a menos que CORS_ORIGINS seja definida.
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "" if NA_VERCEL else "*").split(",") if o.strip()]

# Documentação interativa (/docs). Desligada na Vercel para não expor o mapa
# das rotas; DOCS=1 liga de novo.
DOCS_ATIVOS = os.getenv("DOCS", "0" if NA_VERCEL else "1") == "1"

# Limite de tentativas de login erradas por usuário e endereço.
LOGIN_MAX_FALHAS = int(os.getenv("LOGIN_MAX_FALHAS", "5"))
LOGIN_JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "900"))


def hoje():
    """Data de referência para prazos de atividades (fuso de Vitória da Conquista).
    DATA_REFERENCIA=AAAA-MM-DD fixa a data, útil em demonstrações gravadas."""
    from datetime import date, datetime
    from zoneinfo import ZoneInfo
    fixa = os.getenv("DATA_REFERENCIA", "")
    if fixa:
        return date.fromisoformat(fixa)
    return datetime.now(ZoneInfo("America/Bahia")).date()
