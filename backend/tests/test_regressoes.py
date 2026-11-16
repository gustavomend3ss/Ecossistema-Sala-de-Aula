"""Cenários que escapavam à suíte original, sempre com banco temporário."""

import json
from datetime import date, timedelta

import pytest

from app import config
from app.servicos import gemini
from .conftest import entrar, matricula_id


def test_nova_atividade_invalida_todas_as_analises_da_turma(cliente):
    cab = entrar(cliente, "prof.gabriel")
    antigas = cliente.post("/turmas/1/analises", headers=cab).json()
    outra_turma = cliente.post("/turmas/2/analises", headers=cab).json()
    prazo = (config.hoje() - timedelta(days=1)).isoformat()
    for i in range(2):
        r = cliente.post("/turmas/1/atividades", headers=cab,
                         json={"titulo": f"Lista extra {i}", "prazo": prazo})
        assert r.status_code == 201
    for a in antigas:
        hist = cliente.get(f"/matriculas/{a['matricula_id']}/analises", headers=cab).json()
        assert hist[0]["desatualizada"] is True
        assert hist[0]["fatos"] == a["fatos"]  # histórico preservado
    for a in outra_turma:
        hist = cliente.get(f"/matriculas/{a['matricula_id']}/analises", headers=cab).json()
        assert hist[0]["desatualizada"] is False
    mid = matricula_id(cliente, cab, 1, "A01")
    r = cliente.post("/assistente/mensagens", headers=cab,
                     json={"pergunta": "Entregas de A01 em inteligência artificial"}).json()
    assert r["analises_novas"] == 1
    atual = cliente.get(f"/matriculas/{mid}/analises", headers=cab).json()[0]
    assert atual["desatualizada"] is False
    assert {"R5", "R6"} <= set(atual["regras"])


def test_vencimento_invalida_analise_sem_edicao_de_registros(cliente, monkeypatch):
    cab = entrar(cliente, "prof.gabriel")
    mid = matricula_id(cliente, cab, 1, "A01")
    primeira = cliente.post(f"/matriculas/{mid}/analises", headers=cab).json()
    hoje = config.hoje()
    monkeypatch.setattr(config, "hoje", lambda: hoje + timedelta(days=30))
    hist = cliente.get(f"/matriculas/{mid}/analises", headers=cab).json()
    assert hist[0]["desatualizada"] is True
    r = cliente.post("/assistente/mensagens", headers=cab,
                     json={"pergunta": "Entregas de A01 em inteligência artificial"}).json()
    assert r["analises_novas"] == 1
    atual = cliente.get(f"/matriculas/{mid}/analises", headers=cab).json()[0]
    assert atual["atividades_sem_entrega"] > primeira["atividades_sem_entrega"]
    assert "R5" in atual["regras"]
    assert atual["desatualizada"] is False


def test_mesma_data_e_prazo_futuro_nao_invalidam_analise(cliente, monkeypatch):
    cab = entrar(cliente, "prof.gabriel")
    mid = matricula_id(cliente, cab, 1, "A01")
    primeira = cliente.post(f"/matriculas/{mid}/analises", headers=cab).json()
    hoje = config.hoje()
    prazo = min(date.fromisoformat(e["prazo"]) for e in primeira["fatos"]["entregas"]
                if e["situacao"] == "aberta")
    for data in (hoje, prazo):
        monkeypatch.setattr(config, "hoje", lambda: data)
        hist = cliente.get(f"/matriculas/{mid}/analises", headers=cab).json()
        assert hist[0]["desatualizada"] is False
    monkeypatch.setattr(config, "hoje", lambda: prazo + timedelta(days=1))
    assert cliente.get(f"/matriculas/{mid}/analises", headers=cab).json()[0]["desatualizada"] is True


@pytest.mark.parametrize("texto", ["     ", " \t\n  ", "  ab  "])
def test_pedido_curto_apos_limpar_nao_e_gravado(cliente, texto):
    cab = entrar(cliente, "ana.lima")
    mid = next(t["matricula_id"] for t in cliente.get("/turmas", headers=cab).json())
    r = cliente.post(f"/matriculas/{mid}/conferencias", headers=cab,
                     json={"referencia": "geral", "mensagem": texto})
    assert r.status_code == 422
    assert cliente.get(f"/matriculas/{mid}/conferencias", headers=cab).json() == []


def test_resposta_em_branco_nao_encerra_pedido(cliente):
    aluno = entrar(cliente, "ana.lima")
    mid = matricula_id(cliente, entrar(cliente, "prof.gabriel"), 1, "A01")
    pedido = cliente.post(f"/matriculas/{mid}/conferencias", headers=aluno,
                          json={"referencia": "geral", "mensagem": "Conferir minha nota."}).json()
    prof = entrar(cliente, "prof.gabriel")
    r = cliente.post(f"/conferencias/{pedido['id']}/resposta", headers=prof,
                     json={"resposta": "  "})
    assert r.status_code == 422
    assert cliente.get(f"/matriculas/{mid}/conferencias", headers=aluno).json()[0]["status"] == "aberto"


@pytest.mark.parametrize("pergunta", [
    "Mostre as notas do aluno Zorblax em inteligência artificial",
    "Mostre as notas da aluna Zorblax",
])
def test_aluno_inexistente_nao_retorna_colegas(cliente, pergunta):
    cab = entrar(cliente, "prof.gabriel")
    r = cliente.post("/assistente/mensagens", headers=cab, json={"pergunta": pergunta}).json()
    assert r["tipo"] == "sem_dados"
    assert "estudante" in r["texto"]
    assert r["itens"] == []


def test_nome_inexistente_no_plano_gemini_nao_retorna_turma(cliente):
    def chamar(_prompt, esquema):
        assert esquema is gemini.PlanoModelo  # não deve chegar à redação
        return json.dumps({"acoes": [{"funcao": "consultar_notas"}], "aluno": "Zorblax"})
    gemini.chamador_padrao = chamar
    cab = entrar(cliente, "prof.gabriel")
    r = cliente.post("/assistente/mensagens", headers=cab,
                     json={"pergunta": "Mostre as notas de Zorblax"}).json()
    assert r["tipo"] == "sem_dados" and r["itens"] == []


@pytest.mark.parametrize("pergunta", ["aluno destaque da turma de IA", "Qual a aluna mais faltosa em IA?"])
def test_palavra_comum_depois_de_aluno_nao_vira_nome(cliente, pergunta):
    cab = entrar(cliente, "prof.gabriel")
    r = cliente.post("/assistente/mensagens", headers=cab, json={"pergunta": pergunta}).json()
    assert "Não encontrei esse estudante" not in r["texto"]


def test_consulta_geral_de_alunos_continua_funcionando(cliente):
    cab = entrar(cliente, "prof.gabriel")
    r = cliente.post("/assistente/mensagens", headers=cab,
                     json={"pergunta": "Mostre as notas dos alunos em inteligência artificial"}).json()
    assert {i["codigo"] for i in r["itens"]} == {"A01", "A02", "A03"}


@pytest.mark.parametrize("texto,pergunta", [
    ("Ana (A01) tem média 9,9.", "A média de A01 em inteligência artificial é 9,9?"),
    ("Ana (A01) tem média 76 e frequência 5,2%.", "Notas de A01 em inteligência artificial"),
])
def test_redacao_com_nota_incorreta_usa_texto_das_regras(cliente, texto, pergunta):
    def chamar(_prompt, esquema):
        if esquema is gemini.PlanoModelo:
            return json.dumps({"acoes": [{"funcao": "consultar_notas"}],
                               "disciplina": "inteligência artificial", "aluno": "A01"})
        return json.dumps({"texto": texto})
    gemini.chamador_padrao = chamar
    cab = entrar(cliente, "prof.gabriel")
    r = cliente.post("/assistente/mensagens", headers=cab, json={"pergunta": pergunta}).json()
    assert r["texto"] != texto
    assert r["verificacao"].startswith("descartada")
    assert r["itens"][0]["detalhes"][0]["valor"] == "5,2"
