"""Configuração lida de variáveis de ambiente (nada de senha no repositório)."""

import hashlib
import hmac
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

# Na Vercel (serviço "api"), o único lugar gravável é /tmp.
NA_VERCEL = bool(os.getenv("VERCEL"))


def _url_do_banco() -> str:
    """DATABASE_URL (ou POSTGRES_URL, nome usado pela integração Neon da Vercel).
    O SQLAlchemy precisa do driver no esquema: postgres:// vira
    postgresql+psycopg://. Sem banco configurado, SQLite local (ou em /tmp na
    Vercel, onde cada instância teria o próprio banco: serve só para teste)."""
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or ""
    if not url:
        return "sqlite:////tmp/ecossistema.db" if NA_VERCEL else "sqlite:///./ecossistema.db"
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


DATABASE_URL = _url_do_banco()
BANCO_COMPARTILHADO = not DATABASE_URL.startswith("sqlite")

# Chave que assina os tokens de acesso. O certo é definir SECRET_KEY no
# ambiente (na Vercel: Settings > Environment Variables). A chave fixa abaixo
# está no repositório público e só vale fora da Vercel, em desenvolvimento.
# Na Vercel sem SECRET_KEY, a chave é derivada de um valor que todas as
# instâncias compartilham e que é secreto: o endereço do banco. Sem banco
# externo, cada instância sorteia a sua (e também teria o próprio SQLite).
CHAVE_DE_DESENVOLVIMENTO = "ecossistema-academico-chave-de-desenvolvimento"


def _chave_de_assinatura() -> str:
    if os.getenv("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    if not NA_VERCEL:
        return CHAVE_DE_DESENVOLVIMENTO
    # Só o endereço do banco serve de semente: ele é secreto. URL e id do
    # deploy são públicos, e com eles a chave seria previsível.
    semente = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or ""
    if not semente:
        return secrets.token_urlsafe(32)
    return hmac.new(CHAVE_DE_DESENVOLVIMENTO.encode(), semente.encode(), hashlib.sha256).hexdigest()


SECRET_KEY = _chave_de_assinatura()

# Recria os dados fictícios quando o banco está vazio (usado na Vercel, onde o
# SQLite fica em /tmp e some quando a função esfria).
SEMEAR_SE_VAZIO = os.getenv("SEMEAR_SE_VAZIO", "1" if NA_VERCEL else "0") == "1"

# Validade do token de sessão, em horas.
SESSAO_HORAS = int(os.getenv("SESSAO_HORAS", "12"))

# Gemini: interpreta perguntas e redige respostas do assistente a partir dos
# fatos já calculados. Sem chave, tudo continua funcionando com as regras.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "15"))

# Correspondência aproximada (RapidFuzz), em pontos de 0 a 100.
# ACEITE: a partir daqui o nome é reconhecido sem perguntar.
# SUGESTAO: entre SUGESTAO e ACEITE, o assistente pede confirmação.
# MARGEM: dois candidatos tão próximos assim viram pergunta de desambiguação.
FUZZY_ACEITE = float(os.getenv("FUZZY_ACEITE", "85"))
FUZZY_SUGESTAO = float(os.getenv("FUZZY_SUGESTAO", "70"))
FUZZY_MARGEM = float(os.getenv("FUZZY_MARGEM", "4"))

# Contexto de conversa: quantas trocas anteriores entram na interpretação.
CONTEXTO_TROCAS = int(os.getenv("CONTEXTO_TROCAS", "4"))

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
