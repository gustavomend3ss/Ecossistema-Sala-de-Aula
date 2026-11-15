"""Assistente docente: perguntas sobre a turma, respostas com evidência.

A pergunta é classificada por palavras-chave em uma intenção. A resposta é
montada só com o resultado do motor de regras, e cada resposta lista as
fontes usadas. Autonomia delimitada: o assistente pode pedir uma análise nova
quando a anterior está desatualizada, mas não altera notas nem decide nada.
"""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session

from ..models import Analise, Matricula, Turma, Usuario
from ..motor import DESCRICAO_REGRAS, fmt_num, fmt_pct
from .analises import esta_desatualizada, executar_analise, ultima_analise

AVISO = "O assistente não toma decisões sozinho e não altera notas. Confira os registros antes de agir."

INTENCOES: list[tuple[str, tuple[str, ...]]] = [
    ("acompanhamento", ("acompanh", "alerta", "prioridad", "risco", "atencao",
                        "preocup", "precisa", "critico", "dificuldade")),
    ("pendencias", ("pendenc", "pendent", "nao lancad", "sem nota", "ausente", "incomplet",
                    "faltando", "conferir", "lancar")),
    ("frequencia", ("frequenc", "falta", "presenc", "assiduidade")),
    ("media", ("media", "nota", "desempenho", "rendimento")),
    ("criterios", ("criterio", "regra", "limite", "como funciona", "como voce decide",
                   "explica")),
    ("resumo", ("resumo", "visao geral", "situacao", "panorama", "como esta", "como vai")),
]

ROTULO_PRIORIDADE = {
    "prioridade_alta": "Prioridade alta",
    "alerta_media": "Alerta de média",
    "alerta_frequencia": "Alerta de frequência",
    "conferir_dados": "Conferir dados",
    "sem_alerta": "Sem alerta",
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def classificar(pergunta: str) -> str:
    p = _normalizar(pergunta)
    for intencao, chaves in INTENCOES:
        if any(ch in p for ch in chaves):
            return intencao
    return "ajuda"


def _aluno_citado(pergunta: str, matriculas: list[Matricula]) -> Matricula | None:
    p = _normalizar(pergunta)
    for m in matriculas:
        if re.search(rf"\b{m.codigo.lower()}\b", p):
            return m
    for m in matriculas:
        partes = [x for x in _normalizar(m.aluno.nome).split() if len(x) > 2]
        if partes and partes[0] in p.split():
            return m
    return None


def _analises_atuais(db: Session, turma: Turma, prof: Usuario) -> tuple[list[tuple[Matricula, Analise]], int]:
    """Usa a última análise de cada matrícula; refaz só as desatualizadas."""
    pares, novas = [], 0
    for m in sorted(turma.matriculas, key=lambda x: x.codigo):
        a = ultima_analise(db, m.id)
        if a is None or esta_desatualizada(a, m):
            a = executar_analise(db, m, prof, com_sintese=False)
            novas += 1
        pares.append((m, a))
    return pares, novas


def _detalhes(a: Analise) -> list[dict]:
    regras = set(a.regras)
    c = a.criterio
    return [
        {"rotulo": "Média", "valor": fmt_num(a.media),
         "limite": fmt_num(c.media_minima), "alerta": "R1" in regras,
         "avaliavel": a.media is not None},
        {"rotulo": "Frequência", "valor": fmt_pct(a.frequencia),
         "limite": fmt_pct(c.frequencia_minima), "alerta": "R2" in regras,
         "avaliavel": a.frequencia is not None},
    ]


def _item(m: Matricula, a: Analise, titulo: str) -> dict:
    pend = "; ".join(p["motivo"] for p in a.pendencias) or None
    return {"matricula_id": m.id, "codigo": m.codigo, "aluno": m.aluno.nome,
            "titulo": titulo, "prioridade": a.prioridade,
            "detalhes": _detalhes(a), "observacao": pend, "analise_id": a.id}


def _n_criterios(n: int, sing: str, plur: str) -> str:
    return f"{n} {sing if n == 1 else plur}"


def responder(db: Session, turma: Turma, prof: Usuario, pergunta: str) -> dict:
    intencao = classificar(pergunta)
    pares, novas = _analises_atuais(db, turma, prof)
    c = turma.criterio
    alvo = _aluno_citado(pergunta, [m for m, _ in pares])
    itens: list[dict] = []
    regras_usadas: set[str] = set()

    if alvo is not None and intencao != "criterios":
        intencao = "aluno"
        a = next(a for m, a in pares if m.id == alvo.id)
        itens.append(_item(alvo, a, ROTULO_PRIORIDADE[a.prioridade]))
        regras_usadas |= set(a.regras)
        texto = f"{alvo.aluno.nome} ({alvo.codigo}): {a.motivo}"

    elif intencao == "acompanhamento":
        com_alerta = [(m, a) for m, a in pares
                      if a.prioridade in ("prioridade_alta", "alerta_media", "alerta_frequencia")]
        com_pend = [(m, a) for m, a in pares if a.pendencias]
        for m, a in com_alerta:
            n = len({"R1", "R2"} & set(a.regras))
            itens.append(_item(m, a, f"{m.aluno.nome} apresenta "
                               f"{_n_criterios(n, 'critério', 'critérios')} de atenção."))
            regras_usadas |= set(a.regras)
        for m, a in com_pend:
            if (m, a) in com_alerta:
                continue
            itens.append(_item(m, a, f"{m.aluno.nome} tem registro pendente; "
                               "um indicador ainda não pode ser avaliado."))
            regras_usadas.add("R4")
        if itens:
            texto = (f"{_n_criterios(len(com_alerta), 'estudante tem', 'estudantes têm')} "
                     f"alerta pelos critérios {c.versao}"
                     + (f" e {_n_criterios(len(com_pend), 'tem', 'têm')} dado pendente." if com_pend else "."))
        else:
            texto = f"Nenhum estudante aciona alerta pelos critérios {c.versao}, e não há pendências."

    elif intencao == "pendencias":
        for m, a in pares:
            if a.pendencias:
                itens.append(_item(m, a, f"{m.aluno.nome}: indicador não avaliável."))
                regras_usadas.add("R4")
        texto = (f"{_n_criterios(len(itens), 'matrícula tem', 'matrículas têm')} dado pendente. "
                 "Nota não lançada continua ausente e nunca é tratada como zero."
                 if itens else "Não há notas nem presenças pendentes nesta turma.")

    elif intencao == "frequencia":
        for m, a in sorted(pares, key=lambda p: (p[1].frequencia is None, p[1].frequencia or 0)):
            itens.append(_item(m, a, f"{m.aluno.nome}: frequência {fmt_pct(a.frequencia)}"
                               + (f" ({a.presencas} de {a.unidades_consideradas} unidades-aula)"
                                  if a.frequencia is not None else "")))
            if "R2" in a.regras:
                regras_usadas.add("R2")
        abaixo = sum(1 for _, a in pares if "R2" in a.regras)
        texto = (f"Limite de frequência em {c.versao}: {fmt_pct(c.frequencia_minima)}. "
                 f"{_n_criterios(abaixo, 'estudante está', 'estudantes estão')} abaixo dele.")

    elif intencao == "media":
        for m, a in sorted(pares, key=lambda p: (p[1].media is None, p[1].media or 0)):
            itens.append(_item(m, a, f"{m.aluno.nome}: média {fmt_num(a.media)}"))
            if "R1" in a.regras:
                regras_usadas.add("R1")
        abaixo = sum(1 for _, a in pares if "R1" in a.regras)
        sem = sum(1 for _, a in pares if a.media is None)
        texto = (f"Média mínima didática em {c.versao}: {fmt_num(c.media_minima)}. "
                 f"{_n_criterios(abaixo, 'estudante está', 'estudantes estão')} abaixo"
                 + (f"; {_n_criterios(sem, 'média ainda não pode ser avaliada', 'médias ainda não podem ser avaliadas')} "
                    "por falta de nota." if sem else "."))

    elif intencao == "criterios":
        regras_usadas = {"R1", "R2", "R3", "R4", "R5"}
        texto = (f"Uso o perfil {c.versao}: média mínima {fmt_num(c.media_minima)} e frequência "
                 f"mínima {fmt_pct(c.frequencia_minima)}, comparadas com 'menor que'. "
                 "Primeiro confiro se os dados estão completos (R4); depois aplico R1 e R2 "
                 "e, se as duas valerem, derivo R3 por encadeamento para a frente. Quando um "
                 "registro muda, faço nova análise e guardo a anterior (R5). Os limites são "
                 "didáticos e não são os critérios oficiais da instituição.")

    elif intencao == "resumo":
        cont: dict[str, int] = {}
        for m, a in pares:
            cont[a.prioridade] = cont.get(a.prioridade, 0) + 1
            itens.append(_item(m, a, f"{m.aluno.nome}: {ROTULO_PRIORIDADE[a.prioridade].lower()}"))
            regras_usadas |= set(a.regras)
        partes = [f"{v} {ROTULO_PRIORIDADE[k].lower()}" for k, v in cont.items()]
        texto = f"{turma.disciplina} tem {len(pares)} estudantes: " + ", ".join(partes) + "."

    else:
        texto = ("Posso responder sobre a turma com base nos registros e nas regras. "
                 "Experimente: \"Quem precisa de acompanhamento?\", \"Há notas pendentes?\", "
                 "\"Como está a frequência?\", \"Fale sobre a A01\" ou \"Quais critérios você usa?\"")

    if intencao != "criterios":
        regras_usadas.discard("R5")
    fontes = [{"titulo": "Registros da turma",
               "descricao": "Notas, frequência e lançamentos"}]
    if regras_usadas:
        lista = sorted(regras_usadas)
        nomes = ", ".join(lista[:-1]) + (" e " if len(lista) > 1 else "") + lista[-1]
        fontes.append({"titulo": f"Regras {nomes}",
                       "descricao": "; ".join(DESCRICAO_REGRAS[r] for r in lista)})
    fontes.append({"titulo": f"Perfil {c.versao}",
                   "descricao": f"Média {fmt_num(c.media_minima)} • Frequência {fmt_pct(c.frequencia_minima)}"})

    return {"pergunta": pergunta, "intencao": intencao, "texto": texto,
            "itens": itens, "fontes": fontes, "analises_novas": novas, "aviso": AVISO}
