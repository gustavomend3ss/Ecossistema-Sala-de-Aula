"""Ponto de entrada da API na Vercel.

A Vercel executa este arquivo como função Python. Todas as rotas da API ficam
sob /api, no mesmo domínio do app Flutter, então o navegador não precisa de
CORS. Sem DATABASE_URL, o banco é um SQLite em /tmp, recriado com os dados
fictícios quando a função esfria. Para dados persistentes, configure
DATABASE_URL com um PostgreSQL (por exemplo, Supabase ou Neon).
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/ecossistema.db")
os.environ.setdefault("SEMEAR_SE_VAZIO", "1")

from fastapi import FastAPI  # noqa: E402

from app.main import app as api  # noqa: E402

app = FastAPI(title="Ecossistema de Gestão Acadêmica", docs_url=None, redoc_url=None)
app.mount("/api", api)
