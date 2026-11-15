"""Fluxo completo pela API: casos T01 a T09 do Quadro 9 e requisitos RF01 a RF07."""

import json

from app.servicos import sintese

from .conftest import entrar, matricula_id


# ---------------------------------------------------------------- RF01
def test_rf01_credencial_invalida_tem_mensagem_clara(cliente):
    r = cliente.post("/sessoes", json={"login": "prof.gabriel", "senha": "errada"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Usuário ou senha incorretos."


def test_rf01_sem_token_nao_entra(cliente):
    assert cliente.get("/turmas").status_code == 401


# ---------------------------------------------------------------- T01
def test_t01_analise_pela_api(cliente):
    cab = entrar(cliente, "prof.gabriel")
    mid = matricula_id(cliente, cab, 1, "A01")
    r = cliente.post(f"/matriculas/{mid}/analises", headers=cab)
    assert r.status_code == 201
    a = r.json()
    assert a["media"] == 5.2 and a["frequencia"] == 76.0
    assert a["regras"] == ["R1", "R2", "R3"]
    assert a["versao_criterios"] == "DEMO-v1"
    assert a["fatos"]["notas"][0]["valor"] == 5.0   # cópia fixa dos dados usados


# ---------------------------------------------------------------- T05 + RF06
def test_t05_correcao_gera_nova_analise_e_preserva_anterior(cliente):
    cab = entrar(cliente, "prof.gabriel")
    mid = matricula_id(cliente, cab, 1, "A01")
    primeira = cliente.post(f"/matriculas/{mid}/analises", headers=cab).json()

    reg = cliente.get(f"/matriculas/{mid}/registros", headers=cab).json()
    av1 = reg["avaliacoes"][0]["avaliacao_id"]
    r = cliente.put(f"/matriculas/{mid}/notas/{av1}", headers=cab, json={"valor": 7.6})
    assert r.status_code == 200
    assert r.json()["indicadores"]["media"] == 6.5

    hist = cliente.get(f"/matriculas/{mid}/analises", headers=cab).json()
    assert hist[0]["desatualizada"] is True        # anterior aparece desatualizada

    nova = cliente.post(f"/matriculas/{mid}/analises", headers=cab).json()
    assert nova["regras"] == ["R2", "R5"]
    r5 = next(x for x in nova["acionadas"] if x["regra"] == "R5")
    assert r5["evidencia"]["analise_anterior_id"] == primeira["id"]

    hist = cliente.get(f"/matriculas/{mid}/analises", headers=cab).json()
    assert [h["id"] for h in hist] == [nova["id"], primeira["id"]]
    assert hist[1]["regras"] == ["R1", "R2", "R3"]   # anterior intacta

    alteracoes = cliente.get(f"/matriculas/{mid}/historico", headers=cab).json()
    assert alteracoes[0]["valor_anterior"] == "5,0" and alteracoes[0]["valor_novo"] == "7,6"
    assert alteracoes[0]["autor"] == "Prof. Gabriel"


def test_rf06_revisao_guarda_autor_e_data(cliente):
    cab = entrar(cliente, "prof.gabriel")
    mid = matricula_id(cliente, cab, 1, "A01")
    a = cliente.post(f"/matriculas/{mid}/analises", headers=cab).json()
    r = cliente.post(f"/analises/{a['id']}/revisoes", headers=cab,
                     json={"decisao": "confirmado", "observacao": "Conversar após a aula."})
    assert r.status_code == 201
    rev = r.json()["revisoes"][0]
    assert rev["autor"] == "Prof. Gabriel" and rev["criado_em"]


# ---------------------------------------------------------------- T06 / RF02
def test_t06_aluno_nao_ve_outra_matricula(cliente):
    prof = entrar(cliente, "prof.gabriel")
    mid_bruno = matricula_id(cliente, prof, 1, "A02")
    ana = entrar(cliente, "ana.lima")
    r = cliente.get(f"/matriculas/{mid_bruno}/registros", headers=ana)
    assert r.status_code == 404
    assert "Bruno" not in r.text and "7" not in r.json()["detail"]


def test_t06_professor_sem_vinculo_nao_ve_turma(cliente):
    prof = entrar(cliente, "prof.gabriel")
    assert cliente.get("/turmas/3", headers=prof).status_code == 404
    assert all(t["id"] != 3 for t in cliente.get("/turmas", headers=prof).json())


def test_t06_aluno_nao_altera_nota(cliente):
    ana = entrar(cliente, "ana.lima")
    turmas = cliente.get("/turmas", headers=ana).json()
    mid = next(t["matricula_id"] for t in turmas if t["codigo"] == "A01")
    r = cliente.put(f"/matriculas/{mid}/notas/1", headers=ana, json={"valor": 10})
    assert r.status_code == 403


# ---------------------------------------------------------------- T07
def test_t07_nota_fora_da_escala_rejeitada(cliente):
    cab = entrar(cliente, "prof.gabriel")
    mid = matricula_id(cliente, cab, 1, "A02")
    antes = cliente.get(f"/matriculas/{mid}/registros", headers=cab).json()
    av = antes["avaliacoes"][0]["avaliacao_id"]
    r = cliente.put(f"/matriculas/{mid}/notas/{av}", headers=cab, json={"valor": 11})
    assert r.status_code == 422
    assert r.json()["detail"] == "A nota 11,0 está fora da escala de 0 a 10,0. Nada foi salvo."
    depois = cliente.get(f"/matriculas/{mid}/registros", headers=cab).json()
    assert depois["versao_registros"] == antes["versao_registros"]
    assert depois["avaliacoes"][0]["valor"] == 7.0


# ---------------------------------------------------------------- T08 / RF07
def test_t08_pedido_de_conferencia_nao_altera_nota(cliente):
    ana = entrar(cliente, "ana.lima")
    turmas = cliente.get("/turmas", headers=ana).json()
    mid = next(t["matricula_id"] for t in turmas if t["codigo"] == "A01")
    antes = cliente.get(f"/matriculas/{mid}/registros", headers=ana).json()
    av = antes["avaliacoes"][1]["avaliacao_id"]

    r = cliente.post(f"/matriculas/{mid}/conferencias", headers=ana,
                     json={"referencia": f"avaliacao:{av}",
                           "mensagem": "Acho que a Avaliação 2 foi 6,4 e não 5,4."})
    assert r.status_code == 201
    assert r.json()["referencia_rotulo"] == "Avaliação 2"

    depois = cliente.get(f"/matriculas/{mid}/registros", headers=ana).json()
    assert depois["avaliacoes"][1]["valor"] == 5.4
    assert depois["versao_registros"] == antes["versao_registros"]

    prof = entrar(cliente, "prof.gabriel")
    pedidos = cliente.get(f"/matriculas/{mid}/conferencias", headers=prof).json()
    assert pedidos[0]["status"] == "aberto"
    r = cliente.post(f"/conferencias/{pedidos[0]['id']}/resposta", headers=prof,
                     json={"resposta": "Conferi a prova: a nota é 5,4."})
    assert r.json()["status"] == "respondido"


# ---------------------------------------------------------------- T09
def _analisar_a01(cliente):
    cab = entrar(cliente, "prof.gabriel")
    mid = matricula_id(cliente, cab, 1, "A01")
    return cliente.post(f"/matriculas/{mid}/analises", headers=cab).json()


def test_t09_sintese_com_numero_errado_e_descartada(cliente):
    sintese.chamador_padrao = lambda _p: json.dumps({
        "texto": "Média 5,8 abaixo de 6,0 e frequência de 76% abaixo de 80%; R1, R2 e R3.",
        "regras_citadas": ["R1", "R2", "R3"]})
    a = _analisar_a01(cliente)
    assert a["sintese"] is None
    assert a["sintese_status"].startswith("descartada")
    assert a["regras"] == ["R1", "R2", "R3"]      # relatório estruturado continua


def test_t09_servico_fora_do_ar(cliente):
    def falha(_p):
        raise ConnectionError("sem rede")
    sintese.chamador_padrao = falha
    a = _analisar_a01(cliente)
    assert a["sintese"] is None and a["sintese_status"].startswith("indisponivel")
    assert a["motivo"].startswith("A média 5,2")


def test_t09_sintese_que_inventa_causa_e_descartada(cliente):
    sintese.chamador_padrao = lambda _p: json.dumps({
        "texto": "A média 5,2 e a frequência de 76% acionam R1, R2 e R3, "
                 "provavelmente por desmotivação.",
        "regras_citadas": ["R1", "R2", "R3"]})
    assert "desmotiv" not in (_analisar_a01(cliente)["sintese"] or "")


def test_t09_sintese_fiel_e_aprovada(cliente):
    sintese.chamador_padrao = lambda _p: json.dumps({
        "texto": "A média 5,2 ficou abaixo de 6,0 (R1) e a frequência de 76% ficou "
                 "abaixo de 80% (R2); juntas, levam à prioridade de conferência R3.",
        "regras_citadas": ["R1", "R2", "R3"]})
    a = _analisar_a01(cliente)
    assert a["sintese_status"] == "aprovada"
    assert a["sintese"].startswith("A média 5,2")


def test_sintese_que_esquece_pendencia_e_descartada(cliente):
    sintese.chamador_padrao = lambda _p: json.dumps({
        "texto": "A frequência de 92% está dentro do esperado.", "regras_citadas": []})
    cab = entrar(cliente, "prof.gabriel")
    mid = matricula_id(cliente, cab, 1, "A03")
    a = cliente.post(f"/matriculas/{mid}/analises", headers=cab).json()
    assert a["sintese"] is None and "R4" in a["sintese_status"]


# ---------------------------------------------------------------- assistente
def test_assistente_quem_precisa_de_acompanhamento(cliente):
    cab = entrar(cliente, "prof.gabriel")
    r = cliente.post("/turmas/1/assistente", headers=cab,
                     json={"pergunta": "Quem precisa de acompanhamento nesta turma?"}).json()
    assert r["intencao"] == "acompanhamento"
    nomes = [i["aluno"] for i in r["itens"]]
    assert nomes == ["Ana Lima", "Carla Dias"]
    assert r["itens"][0]["detalhes"][0] == {
        "rotulo": "Média", "valor": "5,2", "limite": "6,0", "alerta": True, "avaliavel": True}
    assert any(f["titulo"] == "Perfil DEMO-v1" for f in r["fontes"])


def test_assistente_pendencias(cliente):
    cab = entrar(cliente, "prof.gabriel")
    r = cliente.post("/turmas/1/assistente", headers=cab,
                     json={"pergunta": "Há notas pendentes?"}).json()
    assert r["intencao"] == "pendencias"
    assert [i["codigo"] for i in r["itens"]] == ["A03"]


def test_assistente_bloqueado_para_aluno(cliente):
    ana = entrar(cliente, "ana.lima")
    r = cliente.post("/turmas/1/assistente", headers=ana, json={"pergunta": "Quem?"})
    assert r.status_code == 403


def test_area_do_aluno(cliente):
    ana = entrar(cliente, "ana.lima")
    d = cliente.get("/aluno/desempenho", headers=ana).json()
    ia = next(x for x in d if x["codigo"] == "A01")
    assert ia["indicadores"]["media"] == 5.2
    assert ia["indicadores"]["presencas"] == 19
    assert ia["indicadores"]["unidades_consideradas"] == 25
