"""Motor de regras isolado: casos T01 a T05 do Quadro 9 e bordas."""

from app.motor import Criterios, Fatos, NotaFato, PresencaFato, analisar, montar_motivo

DEMO = Criterios("DEMO-v1", media_minima=6.0, frequencia_minima=80.0)


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
