"""Motor de regras isolado: casos T01 a T05 do Quadro 9 e bordas."""

from app.motor import Criterios, Fatos, NotaFato, PresencaFato, analisar, montar_motivo

DEMO = Criterios("DEMO-v2", media_minima=6.0, frequencia_minima=80.0)


def fatos(notas, presentes, total, sem_registro=0):
    pres = [PresencaFato(f"Aula {i + 1}", 1, i < presentes) for i in range(total)]
    pres += [PresencaFato(f"Aula {total + i + 1}", 1, None) for i in range(sem_registro)]
    return Fatos(
        matricula="X",
        notas=tuple(NotaFato(f"Avaliação {i + 1}", 1.0, True, v) for i, v in enumerate(notas)),
        presencas=tuple(pres))


def test_t01_a01_completo_aciona_r1_r2_r3():
    r = analisar(fatos([5.0, 5.4], 19, 25), DEMO)
    assert r.media == 5.2
    assert r.frequencia == 76.0
    assert [a.regra for a in r.acionadas] == ["R1", "R2", "R3"]
    assert r.prioridade == "prioridade_alta"
    assert montar_motivo(r, DEMO) == (
        "A média 5,2 está abaixo do limite didático de 6,0 e a frequência de 76% "
        "está abaixo de 80%. As regras R1 e R2 sustentam a prioridade de conferência R3.")


def test_t01_evidencia_mostra_dado_e_criterio():
    r = analisar(fatos([5.0, 5.4], 19, 25), DEMO)
    r1 = r.acionadas[0]
    assert r1.evidencia["media_baixa"] == {
        "indicador": "media", "valor": 5.2, "limite": 6.0, "comparacao": "<"}
    assert r.acionadas[2].evidencia == {"derivado_de": ["alerta_frequencia", "alerta_media"]}


def test_t02_fronteira_menor_que():
    r = analisar(fatos([6.0, 6.0], 20, 25), DEMO)
    assert r.media == 6.0 and r.frequencia == 80.0
    assert r.acionadas == []
    assert r.prioridade == "sem_alerta"


def test_t03_nota_ausente_nao_vira_zero():
    r = analisar(fatos([7.0, None], 23, 25), DEMO)
    assert r.media is None
    assert r.frequencia == 92.0
    assert r.regras == ["R4"]
    assert r.pendencias[0].indicador == "media"
    assert "sem nota lançada" in r.pendencias[0].motivo
    # se a ausência virasse zero, a média seria 3,5 e acionaria R1
    assert "alerta_media" not in r.base


def test_t04_nenhuma_aula_sem_divisao_por_zero():
    r = analisar(fatos([7.0, 8.0], 0, 0), DEMO)
    assert r.frequencia is None
    assert r.media == 7.5
    assert r.pendencias[0].indicador == "frequencia"
    assert r.pendencias[0].motivo == "Nenhuma aula registrada."


def test_t05_a01_corrigido_so_r2():
    r = analisar(fatos([7.6, 5.4], 19, 25), DEMO)
    assert r.media == 6.5
    assert [a.regra for a in r.acionadas] == ["R2"]
    assert r.prioridade == "alerta_frequencia"


def test_presenca_sem_registro_gera_pendencia():
    r = analisar(fatos([7.0, 8.0], 20, 20, sem_registro=1), DEMO)
    assert r.frequencia is None
    assert "Presença não registrada" in r.pendencias[0].motivo


def test_nota_fora_da_escala_no_motor_e_inconsistencia():
    r = analisar(fatos([11.0, 8.0], 20, 20), DEMO)
    assert r.media is None
    assert "fora da escala" in r.pendencias[0].motivo


def test_pesos_diferentes():
    f = Fatos("X", (NotaFato("P1", 1.0, True, 4.0), NotaFato("P2", 3.0, True, 8.0)),
              tuple(PresencaFato(f"A{i}", 1, True) for i in range(10)))
    assert analisar(f, DEMO).media == 7.0


def test_mesma_entrada_mesma_saida():
    a = analisar(fatos([5.0, 5.4], 19, 25), DEMO)
    b = analisar(fatos([5.0, 5.4], 19, 25), DEMO)
    assert (a.media, a.frequencia, a.regras) == (b.media, b.frequencia, b.regras)


# ------------------------------------------------- R6 e fatores de certeza
from app.motor import EntregaFato, combinar_fc  # noqa: E402

DEMO2 = Criterios("DEMO-v2", media_minima=6.0, frequencia_minima=80.0, atrasos_maximos=1)


def com_entregas(base, situacoes):
    ents = tuple(EntregaFato(f"Atividade {i + 1}", "2026-10-01", s) for i, s in enumerate(situacoes))
    return Fatos(base.matricula, base.notas, base.presencas, entregas=ents)


def test_r6_acima_do_limite():
    f = com_entregas(fatos([7.0, 8.0], 23, 25), ["entregue", "atrasada", "atrasada"])
    r = analisar(f, DEMO2)
    assert [a.regra for a in r.acionadas] == ["R6"]
    assert r.prioridade == "alerta_entregas"
    assert r.acionadas[0].evidencia["entregas_vencidas"]["valor"] == 2


def test_r6_no_limite_nao_dispara():
    f = com_entregas(fatos([7.0, 8.0], 23, 25), ["entregue", "atrasada", "entregue_atraso"])
    r = analisar(f, DEMO2)
    assert r.acionadas == [] and r.prioridade == "sem_alerta"
    assert r.taxa_entrega == 66.67


def test_atividade_aberta_nao_conta_contra():
    f = com_entregas(fatos([7.0, 8.0], 23, 25), ["aberta", "aberta", "aberta"])
    r = analisar(f, DEMO2)
    assert r.atividades_vencidas == 0 and r.acionadas == [] and r.taxa_entrega is None


def test_fatores_de_certeza_do_a01():
    r = analisar(fatos([5.0, 5.4], 19, 25), DEMO2)
    fc = {a.regra: a.fc for a in r.acionadas}
    assert fc == {"R1": 0.7, "R2": 0.6, "R3": 0.54}   # R3 = min(0,7; 0,6) × 0,9
    assert r.certeza == 0.88                          # 0,7 + 0,6 × (1 − 0,7)


def test_certeza_cresce_com_evidencia_independente():
    f = com_entregas(fatos([5.0, 5.4], 19, 25), ["atrasada", "atrasada", "entregue"])
    r = analisar(f, DEMO2)
    assert r.regras == ["R1", "R2", "R3", "R6"]
    assert r.certeza == 0.94                          # 0,88 + 0,5 × (1 − 0,88)
    assert r.certeza < 1


def test_poucos_dados_reduzem_a_certeza():
    # 3 presenças em 4 aulas: 75% está abaixo de 80%, mas 4 aulas dizem pouco
    r = analisar(fatos([7.0, 8.0], 3, 4), DEMO2)
    assert [a.regra for a in r.acionadas] == ["R2"]
    assert r.acionadas[0].fc == 0.24                  # (4/10) × 0,6


def test_combinacao_mycin():
    assert combinar_fc(0.6, 0.5) == 0.8
    assert combinar_fc(0.0, 0.7) == 0.7
