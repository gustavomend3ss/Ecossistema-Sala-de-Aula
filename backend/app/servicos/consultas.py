"""Funções acadêmicas autorizadas do assistente docente.

São as únicas operações que o assistente (e o Gemini, quando ligado) pode
acionar. Todas recebem o usuário autenticado, trabalham só com as turmas e
matrículas que ele pode ver e só leem dados: nenhuma altera nota, presença ou
entrega. As decisões acadêmicas (alertas, prioridade, grau de certeza) vêm
sempre do motor de regras, por meio das análises gravadas.

Cada função devolve um Bloco: texto pronto, itens por estudante, regras
usadas, ids das matrículas (para o contexto da conversa) e um resumo
minimizado dos fatos, que é o único dado acadêmico enviado ao Gemini.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Analise, Matricula, Turma, Usuario, VinculoProfessorTurma
from ..motor import DESCRICAO_REGRAS, fmt_num, fmt_pct
from .analises import esta_desatualizada, executar_analise, ultima_analise

ROTULO_PRIORIDADE = {
    "prioridade_alta": "Prioridade alta",
    "alerta_media": "Alerta de média",
    "alerta_frequencia": "Alerta de frequência",
    "alerta_entregas": "Alerta de entregas",
    "conferir_dados": "Conferir dados",
    "sem_alerta": "Sem alerta",
}
COM_ALERTA = ("prioridade_alta", "alerta_media", "alerta_frequencia", "alerta_entregas")

Par = tuple[Matricula, Analise]


# ------------------------------------------------------------ permissões
def turmas_autorizadas(db: Session, u: Usuario) -> list[Turma]:
    """Professor: turmas vinculadas a ele. Aluno: turmas em que está matriculado."""
    if u.perfil == "professor":
        q = (select(Turma).join(VinculoProfessorTurma, VinculoProfessorTurma.turma_id == Turma.id)
             .where(VinculoProfessorTurma.professor_id == u.id))
    elif u.perfil == "aluno":
        q = select(Turma).join(Matricula, Matricula.turma_id == Turma.id).where(Matricula.aluno_id == u.id)
    else:
        return []
    return sorted(db.scalars(q).unique().all(), key=lambda t: t.disciplina)


def matriculas_visiveis(u: Usuario, turmas: list[Turma]) -> list[Matricula]:
    out = []
    for t in turmas:
        for m in sorted(t.matriculas, key=lambda x: x.codigo):
            if u.perfil == "professor" or m.aluno_id == u.id:
                out.append(m)
    return out


def analises_atuais(db: Session, u: Usuario, matriculas: list[Matricula]) -> tuple[list[Par], int]:
    """Última análise de cada matrícula; refaz só as desatualizadas (R5).
    Quem pede a análise nova é o próprio usuário, que já tem acesso a ela."""
    pares, novas = [], 0
    for m in matriculas:
        a = ultima_analise(db, m.id)
        if a is None or esta_desatualizada(a, m):
            a = executar_analise(db, m, u, com_sintese=False)
            novas += 1
        pares.append((m, a))
    return pares, novas


# ------------------------------------------------------------ resultado
@dataclass
class Bloco:
    funcao: str
    titulo: str
    texto: str
    itens: list[dict] = field(default_factory=list)
    regras: set[str] = field(default_factory=set)
    matriculas: list[int] = field(default_factory=list)
    fatos: dict = field(default_factory=dict)
    sem_dados: bool = False

    def como_dict(self) -> dict:
        return {"funcao": self.funcao, "titulo": self.titulo, "texto": self.texto,
                "itens": self.itens, "sem_dados": self.sem_dados}


def detalhes(a: Analise) -> list[dict]:
    regras = set(a.regras)
    c = a.criterio
    return [
        {"rotulo": "Média", "valor": fmt_num(a.media),
         "limite": fmt_num(c.media_minima), "alerta": "R1" in regras,
         "avaliavel": a.media is not None, "comparacao": "<", "tipo_limite": "mín."},
        {"rotulo": "Frequência", "valor": fmt_pct(a.frequencia),
         "limite": fmt_pct(c.frequencia_minima), "alerta": "R2" in regras,
         "avaliavel": a.frequencia is not None, "comparacao": "<", "tipo_limite": "mín."},
        {"rotulo": "Sem entrega", "valor": str(a.atividades_sem_entrega),
         "limite": str(c.atrasos_maximos), "alerta": "R6" in regras,
         "avaliavel": a.atividades_vencidas > 0, "comparacao": ">", "tipo_limite": "máx."},
    ]


def item(m: Matricula, a: Analise, titulo: str, extra: Optional[dict] = None) -> dict:
    pend = "; ".join(p["motivo"] for p in a.pendencias) or None
    d = {"matricula_id": m.id, "codigo": m.codigo, "aluno": m.aluno.nome,
         "disciplina": m.turma.disciplina, "titulo": titulo, "prioridade": a.prioridade,
         "certeza": a.certeza, "detalhes": detalhes(a), "observacao": pend, "analise_id": a.id}
    if extra:
        d.update(extra)
    return d


def fato(m: Matricula, a: Analise) -> dict:
    """Fatos de um estudante enviados ao Gemini: código e primeiro nome, nada de
    login, e-mail ou identificador interno (minimização de dados, LGPD)."""
    return {"codigo": m.codigo, "nome": m.aluno.nome.split()[0], "disciplina": m.turma.disciplina,
            "media": a.media, "frequencia": a.frequencia,
            "atividades_vencidas": a.atividades_vencidas,
            "atividades_sem_entrega": a.atividades_sem_entrega,
            "regras": list(a.regras), "certeza": a.certeza,
            "prioridade": ROTULO_PRIORIDADE[a.prioridade],
            "pendencias": [p["motivo"] for p in a.pendencias]}


def _n(n: int, sing: str, plur: str) -> str:
    return f"{n} {sing if n == 1 else plur}"


def _turmas_txt(pares: list[Par]) -> str:
    nomes = sorted({m.turma.disciplina for m, _ in pares})
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def _criterio_txt(pares: list[Par]) -> str:
    c = pares[0][0].turma.criterio
    return c.versao


# ------------------------------------------------------------ funções
def consultar_disciplinas(db: Session, u: Usuario, turmas: list[Turma], **_) -> Bloco:
    if not turmas:
        return Bloco("consultar_disciplinas", "Suas turmas", "Você não tem turmas vinculadas.",
                     sem_dados=True)
    linhas = [f"{t.disciplina} ({t.periodo}): {_n(len(t.matriculas), 'estudante', 'estudantes')}"
              for t in turmas]
    return Bloco("consultar_disciplinas", "Suas turmas",
                 "Você tem acesso a: " + "; ".join(linhas) + ".",
                 fatos={"turmas": [{"disciplina": t.disciplina, "estudantes": len(t.matriculas)}
                                   for t in turmas]})


def listar_alunos_em_risco(db: Session, u: Usuario, pares: list[Par], criterio: str = "risco", **_) -> Bloco:
    """Estudantes com indicador de risco pelas regras do motor.
    criterio: risco (qualquer alerta), media (R1), frequencia (R2) ou entregas (R6)."""
    regra_por_criterio = {"media": "R1", "frequencia": "R2", "entregas": "R6"}
    titulo_por_criterio = {"risco": "Estudantes com indicador de risco",
                           "media": "Baixo desempenho (média abaixo do mínimo)",
                           "frequencia": "Muitas faltas (frequência abaixo do mínimo)",
                           "entregas": "Atividades vencidas sem entrega acima do limite"}
    if not pares:
        return Bloco("listar_alunos_em_risco", titulo_por_criterio[criterio],
                     "Não há estudantes neste recorte.", sem_dados=True)
    if criterio == "risco":
        sel = [(m, a) for m, a in pares if a.prioridade in COM_ALERTA]
    else:
        r = regra_por_criterio[criterio]
        sel = [(m, a) for m, a in pares if r in a.regras]
    sel.sort(key=lambda p: -p[1].certeza)
    nao_avaliaveis = [(m, a) for m, a in pares if a.pendencias and (m, a) not in sel]
    if criterio == "media":
        nao_avaliaveis = [(m, a) for m, a in pares if a.media is None]
    elif criterio == "frequencia":
        nao_avaliaveis = [(m, a) for m, a in pares if a.frequencia is None]
    elif criterio == "entregas":
        nao_avaliaveis = []

    itens, regras = [], set()
    for m, a in sel:
        n = len({"R1", "R2", "R6"} & set(a.regras))
        itens.append(item(m, a, f"{m.aluno.nome} ({m.codigo}): {ROTULO_PRIORIDADE[a.prioridade].lower()}, "
                                f"{_n(n, 'critério', 'critérios')} de atenção, grau de certeza {fmt_num(a.certeza, 2)}"))
        regras |= set(a.regras) - {"R5"}
    for m, a in nao_avaliaveis:
        itens.append(item(m, a, f"{m.aluno.nome} ({m.codigo}): ainda não pode ser avaliado(a), há dado pendente"))
        regras.add("R4")

    escopo = _turmas_txt(pares)
    if sel:
        texto = (f"Em {escopo}, {_n(len(sel), 'estudante aparece', 'estudantes aparecem')} "
                 f"pelo critério escolhido ({_criterio_txt(pares)}), do maior para o menor grau de certeza.")
    else:
        texto = f"Em {escopo}, nenhum estudante aciona esse critério ({_criterio_txt(pares)})."
    if nao_avaliaveis:
        texto += f" {_n(len(nao_avaliaveis), 'estudante ainda não pode', 'estudantes ainda não podem')} ser avaliado(s) por falta de registro."
    return Bloco("listar_alunos_em_risco", titulo_por_criterio[criterio], texto, itens, regras,
                 [m.id for m, _ in sel], {"escopo": escopo, "criterio": criterio,
                                         "estudantes": [fato(m, a) for m, a in sel],
                                         "nao_avaliaveis": [fato(m, a) for m, a in nao_avaliaveis]})


def consultar_notas(db: Session, u: Usuario, pares: list[Par], **_) -> Bloco:
    if not pares:
        return Bloco("consultar_notas", "Notas", "Não há estudantes neste recorte.", sem_dados=True)
    itens, fatos, lancadas = [], [], 0
    for m, a in sorted(pares, key=lambda p: (p[1].media is None, p[1].media or 0)):
        notas = a.fatos.get("notas", [])
        lancadas += sum(1 for n in notas if n["valor"] is not None)
        partes = [f"{n['avaliacao']}: {fmt_num(n['valor']) if n['valor'] is not None else 'não lançada'}"
                  for n in notas]
        itens.append(item(m, a, f"{m.aluno.nome} ({m.codigo}): média {fmt_num(a.media)}",
                          {"linhas": partes}))
        fatos.append({**fato(m, a), "notas": [{"avaliacao": n["avaliacao"], "valor": n["valor"]} for n in notas]})
    escopo = _turmas_txt(pares)
    if lancadas == 0:
        return Bloco("consultar_notas", "Notas",
                     f"Ainda não há notas lançadas em {escopo}. Sem nota, a média não pode ser avaliada (R4).",
                     itens, {"R4"}, [], {"escopo": escopo, "estudantes": fatos}, sem_dados=True)
    c = pares[0][0].turma.criterio
    abaixo = sum(1 for _, a in pares if "R1" in a.regras)
    texto = (f"Notas de {escopo}. Média mínima didática: {fmt_num(c.media_minima)}; "
             f"{_n(abaixo, 'estudante está', 'estudantes estão')} abaixo dela.")
    return Bloco("consultar_notas", "Notas", texto, itens, {"R1"} if abaixo else set(),
                 [m.id for m, _ in pares], {"escopo": escopo, "media_minima": c.media_minima, "estudantes": fatos})


def consultar_frequencia(db: Session, u: Usuario, pares: list[Par], **_) -> Bloco:
    if not pares:
        return Bloco("consultar_frequencia", "Frequência", "Não há estudantes neste recorte.", sem_dados=True)
    escopo = _turmas_txt(pares)
    if all(a.frequencia is None for _, a in pares):
        return Bloco("consultar_frequencia", "Frequência",
                     f"Ainda não há aulas com presença registrada em {escopo}, então a frequência não pode ser avaliada (R4).",
                     regras={"R4"}, sem_dados=True, fatos={"escopo": escopo})
    itens = []
    for m, a in sorted(pares, key=lambda p: (p[1].frequencia is None, p[1].frequencia or 0)):
        extra = (f" ({a.presencas} de {a.unidades_consideradas} unidades-aula)" if a.frequencia is not None else "")
        itens.append(item(m, a, f"{m.aluno.nome} ({m.codigo}): frequência {fmt_pct(a.frequencia)}{extra}"))
    c = pares[0][0].turma.criterio
    abaixo = sum(1 for _, a in pares if "R2" in a.regras)
    texto = (f"Frequência em {escopo}. Mínimo do perfil: {fmt_pct(c.frequencia_minima)}; "
             f"{_n(abaixo, 'estudante está', 'estudantes estão')} abaixo dele.")
    return Bloco("consultar_frequencia", "Frequência", texto, itens, {"R2"} if abaixo else set(),
                 [m.id for m, _ in pares],
                 {"escopo": escopo, "frequencia_minima": c.frequencia_minima, "estudantes": [fato(m, a) for m, a in pares]})


def consultar_entregas(db: Session, u: Usuario, pares: list[Par], **_) -> Bloco:
    escopo = _turmas_txt(pares) if pares else ""
    vencidas = [(m, a) for m, a in pares if a.atividades_vencidas > 0]
    if not vencidas:
        return Bloco("consultar_entregas", "Entregas",
                     f"Nenhuma atividade venceu ainda em {escopo}." if escopo else "Não há estudantes neste recorte.",
                     sem_dados=True, fatos={"escopo": escopo})
    itens = []
    for m, a in sorted(vencidas, key=lambda p: -p[1].atividades_sem_entrega):
        faltam = [e["atividade"] for e in a.fatos.get("entregas", []) if e["situacao"] == "atrasada"]
        itens.append(item(m, a, f"{m.aluno.nome} ({m.codigo}): {a.atividades_sem_entrega} de "
                                f"{a.atividades_vencidas} atividades vencidas sem entrega",
                          {"linhas": faltam}))
    c = pares[0][0].turma.criterio
    com_r6 = sum(1 for _, a in pares if "R6" in a.regras)
    texto = (f"Entregas em {escopo}. O perfil tolera até {c.atrasos_maximos} atividade vencida sem entrega; "
             f"{_n(com_r6, 'estudante passou', 'estudantes passaram')} desse limite (R6).")
    return Bloco("consultar_entregas", "Entregas", texto, itens, {"R6"} if com_r6 else set(),
                 [m.id for m, _ in vencidas],
                 {"escopo": escopo, "atrasos_maximos": c.atrasos_maximos, "estudantes": [fato(m, a) for m, a in vencidas]})


def consultar_pendencias(db: Session, u: Usuario, pares: list[Par], **_) -> Bloco:
    com = [(m, a) for m, a in pares if a.pendencias]
    escopo = _turmas_txt(pares) if pares else ""
    if not com:
        return Bloco("consultar_pendencias", "Registros pendentes",
                     f"Não há notas nem presenças pendentes em {escopo}." if escopo else "Não há estudantes neste recorte.",
                     fatos={"escopo": escopo})
    itens = [item(m, a, f"{m.aluno.nome} ({m.codigo}): indicador não avaliável") for m, a in com]
    return Bloco("consultar_pendencias", "Registros pendentes",
                 f"{_n(len(com), 'matrícula tem', 'matrículas têm')} dado pendente em {escopo}. "
                 "Nota não lançada continua ausente e nunca é tratada como zero (R4).",
                 itens, {"R4"}, [m.id for m, _ in com], {"escopo": escopo, "estudantes": [fato(m, a) for m, a in com]})


def analisar_desempenho(db: Session, u: Usuario, pares: list[Par], **_) -> Bloco:
    """Situação individual de cada estudante do recorte (normalmente um só)."""
    if not pares:
        return Bloco("analisar_desempenho", "Desempenho", "Não encontrei esse estudante.", sem_dados=True)
    itens, regras = [], set()
    textos = []
    for m, a in pares:
        itens.append(item(m, a, f"{m.aluno.nome} ({m.codigo}) em {m.turma.disciplina}: "
                                f"{ROTULO_PRIORIDADE[a.prioridade].lower()}"))
        regras |= set(a.regras) - {"R5"}
        textos.append(f"{m.aluno.nome} ({m.codigo}, {m.turma.disciplina}): {a.motivo}")
    return Bloco("analisar_desempenho", "Desempenho individual", " ".join(textos), itens, regras,
                 [m.id for m, _ in pares], {"estudantes": [fato(m, a) for m, a in pares]})


def explicar_alerta(db: Session, u: Usuario, pares: list[Par], **_) -> Bloco:
    """Por que o motor gerou (ou não) alerta: regras acionadas com evidência e FC."""
    if not pares:
        return Bloco("explicar_alerta", "Explicação do alerta", "Não encontrei esse estudante.", sem_dados=True)
    itens, regras, textos = [], set(), []
    for m, a in pares:
        linhas = []
        for ac in a.acionadas:
            linhas.append(f"{ac['regra']} (FC {fmt_num(ac.get('fc', 0), 2)}): {DESCRICAO_REGRAS.get(ac['regra'], '')}")
        for p in a.pendencias:
            linhas.append(f"R4: {p['motivo']}")
        itens.append(item(m, a, f"{m.aluno.nome} ({m.codigo}): {ROTULO_PRIORIDADE[a.prioridade].lower()}",
                          {"linhas": linhas}))
        regras |= set(a.regras) - {"R5"}
        if a.prioridade == "sem_alerta" and not a.pendencias:
            textos.append(f"{m.aluno.nome} não aciona nenhuma regra de alerta em {m.turma.disciplina}: {a.motivo}")
        else:
            textos.append(f"{m.aluno.nome} ({m.turma.disciplina}): {a.motivo}")
    return Bloco("explicar_alerta", "Explicação do alerta", " ".join(textos), itens, regras,
                 [m.id for m, _ in pares], {"estudantes": [fato(m, a) for m, a in pares]})


# Sugestões ligadas às regras acionadas: o professor avalia e decide.
_INTERVENCOES = {
    "R1": "Retomar os conteúdos das avaliações com nota mais baixa e oferecer atividade de recuperação ou monitoria.",
    "R2": "Conversar com o estudante sobre as faltas e conferir se há presença ainda não registrada.",
    "R3": "Priorizar um contato individual, já que média e frequência estão abaixo do mínimo ao mesmo tempo.",
    "R6": "Combinar um novo prazo para as atividades vencidas e acompanhar a próxima entrega.",
    "R4": "Lançar o registro pendente antes de qualquer conclusão sobre o estudante.",
}


def sugerir_intervencao(db: Session, u: Usuario, pares: list[Par], **_) -> Bloco:
    alvo = [(m, a) for m, a in pares if a.prioridade in COM_ALERTA or a.pendencias]
    if not alvo:
        escopo = _turmas_txt(pares) if pares else "este recorte"
        return Bloco("sugerir_intervencao", "Sugestões de intervenção",
                     f"Nenhum estudante em {escopo} aciona regra de alerta, então não há intervenção indicada pelas regras.",
                     fatos={"escopo": escopo})
    itens, regras = [], set()
    for m, a in sorted(alvo, key=lambda p: -p[1].certeza):
        rs = [r for r in ("R3", "R1", "R2", "R6") if r in a.regras] + (["R4"] if a.pendencias else [])
        linhas = [f"{r}: {_INTERVENCOES[r]}" for r in rs]
        if "R6" in a.regras:
            faltam = [e["atividade"] for e in a.fatos.get("entregas", []) if e["situacao"] == "atrasada"]
            if faltam:
                linhas.append("Atividades vencidas: " + "; ".join(faltam))
        itens.append(item(m, a, f"{m.aluno.nome} ({m.codigo}), {m.turma.disciplina}", {"linhas": linhas}))
        regras |= set(rs)
    return Bloco("sugerir_intervencao", "Sugestões de intervenção",
                 "Sugestões ligadas às regras acionadas, para você avaliar. Elas não substituem a sua decisão.",
                 itens, regras, [m.id for m, _ in alvo],
                 {"estudantes": [{**fato(m, a), "sugestoes": [_INTERVENCOES[r] for r in
                                  ([r for r in ("R3", "R1", "R2", "R6") if r in a.regras] + (["R4"] if a.pendencias else []))]}
                                 for m, a in alvo]})


def explicar_criterios(db: Session, u: Usuario, pares: list[Par], turmas: list[Turma], **_) -> Bloco:
    t = pares[0][0].turma if pares else (turmas[0] if turmas else None)
    if t is None:
        return Bloco("explicar_criterios", "Critérios", "Você não tem turmas vinculadas.", sem_dados=True)
    c = t.criterio
    texto = (f"Uso o perfil {c.versao}: média mínima {fmt_num(c.media_minima)} e frequência mínima "
             f"{fmt_pct(c.frequencia_minima)}, comparadas com 'menor que', e até {c.atrasos_maximos} "
             "atividade vencida sem entrega. Primeiro confiro se os dados estão completos (R4); depois "
             "aplico R1, R2 e R6 e, se R1 e R2 valerem juntas, derivo R3 por encadeamento para a frente. "
             "Cada regra tem um fator de certeza, e os alertas independentes se combinam no grau de certeza. "
             "Quando um registro muda, faço nova análise e guardo a anterior (R5). Os limites são didáticos, "
             "não os critérios oficiais da instituição.")
    return Bloco("explicar_criterios", "Critérios do assistente", texto,
                 regras={"R1", "R2", "R3", "R4", "R5", "R6"},
                 fatos={"versao": c.versao, "media_minima": c.media_minima,
                        "frequencia_minima": c.frequencia_minima, "atrasos_maximos": c.atrasos_maximos})


def resumo_turma(db: Session, u: Usuario, pares: list[Par], **_) -> Bloco:
    if not pares:
        return Bloco("resumo_turma", "Resumo", "Não há estudantes neste recorte.", sem_dados=True)
    cont: dict[str, int] = {}
    itens, regras = [], set()
    for m, a in pares:
        cont[a.prioridade] = cont.get(a.prioridade, 0) + 1
        itens.append(item(m, a, f"{m.aluno.nome} ({m.codigo}): {ROTULO_PRIORIDADE[a.prioridade].lower()}"))
        regras |= set(a.regras) - {"R5"}
    partes = [f"{v} {ROTULO_PRIORIDADE[k].lower()}" for k, v in cont.items()]
    texto = f"{_turmas_txt(pares)}: {_n(len(pares), 'estudante', 'estudantes')}, " + ", ".join(partes) + "."
    return Bloco("resumo_turma", "Resumo", texto, itens, regras, [m.id for m, _ in pares],
                 {"escopo": _turmas_txt(pares), "contagem": cont})


# Lista fechada de funções que o assistente pode acionar.
FUNCOES: dict[str, Callable[..., Bloco]] = {
    "listar_alunos_em_risco": listar_alunos_em_risco,
    "consultar_notas": consultar_notas,
    "consultar_frequencia": consultar_frequencia,
    "consultar_entregas": consultar_entregas,
    "consultar_pendencias": consultar_pendencias,
    "analisar_desempenho": analisar_desempenho,
    "explicar_alerta": explicar_alerta,
    "sugerir_intervencao": sugerir_intervencao,
    "explicar_criterios": explicar_criterios,
    "consultar_disciplinas": consultar_disciplinas,
    "resumo_turma": resumo_turma,
}
CRITERIOS_VALIDOS = ("risco", "media", "frequencia", "entregas")


def fontes(regras: set[str], turmas: list[Turma]) -> list[dict]:
    out = [{"titulo": "Registros da turma", "descricao": "Notas, frequência, entregas e lançamentos"}]
    if regras:
        lista = sorted(regras)
        nomes = ", ".join(lista[:-1]) + (" e " if len(lista) > 1 else "") + lista[-1]
        out.append({"titulo": f"Regras {nomes}",
                     "descricao": "; ".join(DESCRICAO_REGRAS[r] for r in lista if r in DESCRICAO_REGRAS)})
    vistos = set()
    for t in turmas:
        c = t.criterio
        if c.versao in vistos:
            continue
        vistos.add(c.versao)
        out.append({"titulo": f"Perfil {c.versao}",
                    "descricao": f"Média {fmt_num(c.media_minima)} • Frequência {fmt_pct(c.frequencia_minima)} • "
                                 f"até {c.atrasos_maximos} atividade sem entrega"})
    return out
