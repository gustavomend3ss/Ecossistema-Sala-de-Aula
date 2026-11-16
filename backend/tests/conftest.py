import os
import tempfile

# Banco temporário só para os testes, definido antes de importar o app.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", f"sqlite:///{_tmp}/teste.db")
os.environ["GEMINI_API_KEY"] = ""

import pytest                                   # noqa: E402
from fastapi.testclient import TestClient       # noqa: E402

from app import seed, seguranca                 # noqa: E402
from app.main import app                        # noqa: E402
from app.servicos import gemini, sintese        # noqa: E402


@pytest.fixture()
def cliente():
    seed.carregar()
    seguranca._falhas.clear()
    sintese.chamador_padrao = None
    gemini.chamador_padrao = None
    with TestClient(app) as c:
        yield c
    sintese.chamador_padrao = None
    gemini.chamador_padrao = None


def entrar(cliente, login, senha="demo123"):
    r = cliente.post("/sessoes", json={"login": login, "senha": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def matricula_id(cliente, cab, turma_id, codigo):
    turma = cliente.get(f"/turmas/{turma_id}", headers=cab).json()
    return next(e["matricula_id"] for e in turma["estudantes"] if e["codigo"] == codigo)
