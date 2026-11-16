"""Assistente docente: rota legada por turma (Bloco 3, v0.2).

A conversa nova, com contexto, RapidFuzz e Gemini, está em conversa.py.


A pergunta é classificada por palavras-chave em uma intenção. Quando nenhuma
palavra-chave reconhece a pergunta e há chave do Gemini, o modelo só escolhe
a intenção dentro de uma lista fechada (processamento de linguagem natural);
ele nunca escreve a resposta. A resposta é montada só com o resultado do
motor de regras, e cada resposta lista as fontes usadas. Autonomia delimitada: o assistente pode pedir uma análise nova
quando a anterior está desatualizada, mas não altera notas nem decide nada.
"""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session

from typing import Callable, Optional

from .. import config
from ..models import Analise, Matricula, Turma, Usuario
from ..motor import DESCRICAO_REGRAS, fmt_num, fmt_pct
from .consultas import ROTULO_PRIORIDADE, analises_atuais, detalhes, item

AVISO = "O assistente não toma decisões sozinho e não altera notas. Confira os registros antes de agir."

INTENCOES: list[tuple[str, tuple[str, ...]]] = [
    ("acompanhamento", ("acompanh", "alerta", "prioridad", "risco", "atencao",
                        "preocup", "precisa", "critico", "dificuldade")),
    ("entregas", ("entrega", "atividade", "trabalho", "prazo", "lista de exerc",
                  "atrasad", "nao entreg")),
    ("pendencias", ("pendenc", "pendent", "nao lancad", "sem nota", "ausente", "incomplet",
                    "faltando", "conferir", "lancar")),
    ("frequencia", ("frequenc", "falta", "presenc", "assiduidade")),
    ("media", ("media", "nota", "desempenho", "rendimento")),
    ("criterios", ("criterio", "regra", "limite", "como funciona", "como voce decide",
                   "explica")),
    ("resumo", ("resumo", "visao geral", "situacao", "panorama", "como esta", "como vai")),
]

def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


INTENCOES_VALIDAS = [i for i, _ in INTENCOES]

# Função que recebe a pergunta e devolve uma intenção (ou None). Nos testes é
# trocada por uma falsa; em produção usa o Gemini, se houver chave.
Classificador = Callable[[str], Optional[str]]
classificador_padrao: Optional[Classificador] = None


def _classificar_com_gemini(pergunta: str) -> Optional[str]:
    if not config.GEMINI_API_KEY:
        return None
    try:
        import enum

        from google import genai
        from google.genai import types

        Intencao = enum.Enum("Intencao", {i: i for i in INTENCOES_VALIDAS + ["ajuda"]}, type=str)
        cliente = genai.Client(api_key=config.GEMINI_API_KEY)
        resposta = cliente.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=("Classifique a pergunta de um professor sobre a turma dele em UMA "
                      "das intenções: acompanhamento (quem precisa de atenção), entregas "
                      "(atividades e prazos), pendencias (dados não lançados), frequencia, "
                      "media (notas), criterios (como o assistente decide), resumo (visão "
                      "geral) ou ajuda (nenhuma das anteriores).\n\nPergunta: " + pergunta),
            config=types.GenerateContentConfig(
                temperature=0, response_mime_type="text/x.enum", response_schema=Intencao,
                http_options=types.HttpOptions(timeout=int(config.GEMINI_TIMEOUT * 1000))),
        )
        return (resposta.text or "").strip()
    except Exception:
        return None


def classificar(pergunta: str) -> str:
    p = _normalizar(pergunta)
    for intencao, chaves in INTENCOES:
        if any(ch in p for ch in chaves):
            return intencao
    chamar = classificador_padrao or _classificar_com_gemini
    sugerida = chamar(pergunta)
    if sugerida in INTENCOES_VALIDAS:   # a resposta do modelo é conferida
        return sugerida
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
    return analises_atuais(db, prof, sorted(turma.matriculas, key=lambda x: x.codigo))


_detalhes = detalhes


def _item(m: Matricula, a: Analise, titulo: str) -> dict:
    d = item(m, a, titulo)
    d.pop("disciplina", None)
    return d


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
        com_alerta = sorted(
            [(m, a) for m, a in pares if a.prioridade in
             ("prioridade_alta", "alerta_media", "alerta_frequencia", "alerta_entregas")],
            key=lambda p: -p[1].certeza)
        com_pend = [(m, a) for m, a in pares if a.pendencias]
        for m, a in com_alerta:
            n = len({"R1", "R2", "R6"} & set(a.regras))
            itens.append(_item(m, a, f"{m.aluno.nome} apresenta "
                               f"{_n_criterios(n, 'critério', 'critérios')} de atenção "
                               f"(grau de certeza {fmt_num(a.certeza, 2)})."))
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

    elif intencao == "entregas":
        ordenados = sorted(pares, key=lambda p: -p[1].atividades_sem_entrega)
        for m, a in ordenados:
            if a.atividades_vencidas == 0:
                continue
            itens.append(_item(m, a, f"{m.aluno.nome}: {a.atividades_sem_entrega} de "
                               f"{a.atividades_vencidas} atividades vencidas sem entrega"))
            if "R6" in a.regras:
                regras_usadas.add("R6")
        com_r6 = sum(1 for _, a in pares if "R6" in a.regras)
        if itens:
            texto = (f"Limite em {c.versao}: até {c.atrasos_maximos} atividade vencida sem entrega. "
                     f"{_n_criterios(com_r6, 'estudante passou', 'estudantes passaram')} desse limite (R6).")
        else:
            texto = "Nenhuma atividade desta turma venceu ainda."

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
        regras_usadas = {"R1", "R2", "R3", "R4", "R5", "R6"}
        texto = (f"Uso o perfil {c.versao}: média mínima {fmt_num(c.media_minima)} e frequência "
                 f"mínima {fmt_pct(c.frequencia_minima)}, comparadas com 'menor que'. "
                 f"Também observo as entregas: mais de {c.atrasos_maximos} atividade vencida "
                 "sem entrega aciona R6. Primeiro confiro se os dados estão completos (R4); "
                 "depois aplico R1, R2 e R6 e, se R1 e R2 valerem juntas, derivo R3 por "
                 "encadeamento para a frente. Cada regra tem um fator de certeza, e os "
                 "alertas independentes se somam no grau de certeza da necessidade de "
                 "acompanhamento. Quando um registro muda, faço nova análise e guardo a "
                 "anterior (R5). Os limites são didáticos e não são os critérios oficiais "
                 "da instituição.")

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
                 "Experimente: \"Quem precisa de acompanhamento?\", \"Quem está atrasado nas "
                 "entregas?\", \"Há notas pendentes?\", \"Fale sobre a A01\" ou \"Quais "
                 "critérios você usa?\"")

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
                   "descricao": f"Média {fmt_num(c.media_minima)} • Frequência {fmt_pct(c.frequencia_minima)} • "
                                f"até {c.atrasos_maximos} atividade sem entrega"})

    return {"pergunta": pergunta, "intencao": intencao, "texto": texto,
            "itens": itens, "fontes": fontes, "analises_novas": novas, "aviso": AVISO}
