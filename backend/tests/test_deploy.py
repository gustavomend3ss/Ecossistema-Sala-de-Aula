"""Contrato do caminho público /api e inicialização no ambiente serverless."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema


def test_configuracao_vercel_remove_prefixo_do_caminho_observado_pela_api(cliente):
    raiz = Path(__file__).resolve().parents[2]
    config = json.loads((raiz / "vercel.json").read_text())

    def caminho_na_api(publico):
        destino = next(r["destination"] for r in config["rewrites"]
                       if re.fullmatch(r["source"], publico))
        assert destino["service"] == "api"
        # Rewrite dentro do serviço: "/api/:path(.*)?" -> "/:path". Foi o que a
        # produção confirmou; a transformação request.path deixava o /api chegar
        # à API e todas as rotas davam 404.
        for regra in config["services"]["api"]["rewrites"]:
            fonte = regra["source"].replace(":path(.*)?", "(.*)")
            match = re.fullmatch(fonte, publico)
            if match:
                return regra["destination"].replace(":path", match.group(1) or "")
        return publico

    assert caminho_na_api("/api/sessoes") == "/sessoes"
    r = cliente.post(caminho_na_api("/api/sessoes"),
                     json={"login": "prof.gabriel", "senha": "demo123"})
    assert r.status_code == 200
    cab = {"Authorization": f"Bearer {r.json()['token']}"}
    assert cliente.get(caminho_na_api("/api/turmas"), headers=cab).status_code == 200
    assert cliente.get(caminho_na_api("/api/"), headers=cab).status_code == 200
    assert cliente.get(caminho_na_api("/api/inexistente"), headers=cab).status_code == 404


def test_primeira_requisicao_sem_lifespan_cria_banco_e_semeia_uma_vez(tmp_path):
    # Processo separado: config é lida no import, como numa nova função Vercel.
    env = {**os.environ, "VERCEL": "1", "SECRET_KEY": "chave-exclusiva-do-teste",
           "DATABASE_URL": f"sqlite:///{tmp_path}/serverless.db",
           "SEMEAR_SE_VAZIO": "1", "DOCS": "0", "CORS_ORIGINS": "",
           "GEMINI_API_KEY": "", "PYTHONDONTWRITEBYTECODE": "1"}
    script = '''
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Usuario
c = TestClient(app)  # sem context manager: não dispara lifespan
assert c.get('/docs').status_code == 404
assert c.get('/openapi.json').status_code == 404
r = c.post('/sessoes', json={'login': 'prof.gabriel', 'senha': 'demo123'})
assert r.status_code == 200, r.text
assert r.headers['Cache-Control'] == 'no-store'
cab = {'Authorization': 'Bearer ' + r.json()['token']}
assert c.get('/turmas', headers=cab).status_code == 200
with SessionLocal() as db:
    total = db.query(Usuario).count()
assert c.post('/sessoes', json={'login': 'ana.lima', 'senha': 'demo123'}).status_code == 200
with SessionLocal() as db:
    assert db.query(Usuario).count() == total
'''
    r = subprocess.run([sys.executable, "-c", script], env=env,
                       capture_output=True, text=True, timeout=30,
                       cwd=Path(__file__).resolve().parents[1])
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"),
                    reason="Inicialização simultânea exige PostgreSQL")
def test_instancias_iniciam_juntas_em_banco_vazio():
    # Schema exclusivo: não toca nas tabelas nem nos dados dos outros testes.
    url = make_url(os.environ["TEST_DATABASE_URL"])
    schema = "startup_" + uuid.uuid4().hex
    engine = create_engine(url)
    processos = []
    try:
        with engine.begin() as conn:
            conn.execute(CreateSchema(schema))
        isolada = url.update_query_dict({"options": f"-csearch_path={schema}"})
        env = {**os.environ, "VERCEL": "1", "SEMEAR_SE_VAZIO": "1",
               "SECRET_KEY": "chave-do-teste-de-concorrencia", "GEMINI_API_KEY": "",
               "DATABASE_URL": isolada.render_as_string(hide_password=False)}
        script = '''
import sys
from fastapi.testclient import TestClient
from app.main import app
print('PRONTO', flush=True)
sys.stdin.readline()
with TestClient(app) as c:
    r = c.post('/sessoes', json={'login': 'prof.gabriel', 'senha': 'demo123'})
    assert r.status_code == 200, r.text
'''
        for _ in range(3):
            processos.append(subprocess.Popen(
                [sys.executable, "-c", script], env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                cwd=Path(__file__).resolve().parents[1]))
        for processo in processos:
            assert processo.stdout.readline().strip() == "PRONTO"
        for processo in processos:
            processo.stdin.write("\n")
            processo.stdin.flush()
        for processo in processos:
            _, erro = processo.communicate(timeout=45)
            assert processo.returncode == 0, erro
    finally:
        for processo in processos:
            if processo.poll() is None:
                processo.kill()
                processo.communicate()
        with engine.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True, if_exists=True))
        engine.dispose()
