"""Conversa com o assistente docente (arquitetura híbrida).

Fluxo de cada pergunta:

  pergunta -> interpretação (Gemini, ou regras se ele não estiver disponível)
           -> RapidFuzz: disciplina e estudante citados, comparados só com os
              registros que o usuário pode ver
           -> contexto da conversa (turma e estudantes da resposta anterior)
           -> funções autorizadas (consultas.py) -> motor de regras
           -> redação (Gemini, conferida; ou o texto das regras)
           -> resposta com fontes, itens por estudante e sugestões ligadas ao resultado

O contexto fica no banco, preso à conversa e ao usuário que a criou: outra
pessoa não consegue ler nem continuar a conversa. Guardamos apenas ids e
nomes de disciplinas, nunca dados acadêmicos copiados.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..models import Conversa, MensagemConversa, Turma, Usuario, agora, iso_utc
from . import gemini
from .consultas import (CRITERIOS_VALIDOS, FUNCOES, Bloco, analises_atuais, fontes,
                        matriculas_visiveis, turmas_autorizadas)
from .entidades import (escolher_entre, normalizar, resolver_disciplina, resolver_pessoa,
                        termo_no_fim)

log = logging.getLogger("assistente")

AVISO = "O assistente não toma decisões sozinho e não altera notas. Confira os registros antes de agir."

# ------------------------------------------------------------------ interpretação por regras
CONTINUACAO = ("deles", "delas", "desses", "dessas", "destes", "destas", "entre eles", "entre elas",
               "dentre eles", "dentre elas", "esses alunos", "essas alunas", "esses estudantes",
               "quais tambem", "tambem", "e quais", "e quem", "desse grupo", "mesmos alunos",
               "para eles", "para elas", "eles", "elas", "nesses", "nessas")
PRONOME_UNICO = (" ele ", " ela ", " dele ", " dela ", " desse aluno", " dessa aluna",
                 " desse estudante", " dessa estudante", " o aluno", " a aluna")
FORA_DO_ESCOPO = ("altere", "alterar", "mude a nota", "mudar a nota", "troque a nota", "apague", "apagar",
                  "delete", "exclua", "drop table", "update ", "insert ", "select ", " sql",
                  "ignore as instrucoes", "ignore suas instrucoes", "ignore as regras", "senha",
                  "token", "prompt do sistema", "aprove ", "reprove ")
# (palavras-chave, função, critério). A ordem resolve conflitos: frases
# específicas ("muitas faltas", "baixo desempenho") vêm antes das gerais.
REGRAS_INTENCAO: list[tuple[tuple[str, ...], str, Optional[str]]] = [
    (("sugir", "sugest", "intervenc", "o que fazer", "o que posso fazer", "como ajudar",
      "recomend", "estrategia", "como apoiar"), "sugerir_intervencao", None),
    (("por que", "porque", "motivo", "explique", "explica", "explicar", "justifica",
      "entender o alerta"), "explicar_alerta", None),
    (("criterio", "regras", "como voce decide", "como funciona", "quais limites"), "explicar_criterios", None),
    (("quais turmas", "minhas turmas", "quais disciplinas", "minhas disciplinas", "que turmas",
      "que disciplinas"), "consultar_disciplinas", None),
    (("muitas faltas", "muita falta", "faltando muito", "falta muito", "frequencia baixa",
      "baixa frequencia", "abaixo da frequencia", "faltosos", "faltas demais", "faltam muito"),
     "listar_alunos_em_risco", "frequencia"),
    (("baixo desempenho", "desempenho baixo", "nota baixa", "notas baixas", "media baixa",
      "abaixo da media", "indo mal", "rendimento baixo", "mal nas notas", "baixo rendimento"),
     "listar_alunos_em_risco", "media"),
    (("risco", "reprov", "acompanh", "alerta", "atencao", "preocup", "dificuldade", "critico",
      "prioridad", "precisam de ajuda", "precisa de ajuda"), "listar_alunos_em_risco", "risco"),
    (("pendenc", "pendent", "nao lancad", "sem nota", "faltando nota", "incomplet", "lancar"),
     "consultar_pendencias", None),
    (("entrega", "atividade", "trabalho", "prazo", "atrasad", "lista de exerc"), "consultar_entregas", None),
    (("frequencia", "falta", "presenca", "assiduidade", "chamada"), "consultar_frequencia", None),
    (("nota", "media", "desempenho", "rendimento", "avaliac", "prova"), "consultar_notas", None),
    (("resumo", "visao geral", "panorama", "como esta a turma", "como vai a turma", "situacao da turma",
      "como estao"), "resumo_turma", None),
]


def _contem(texto: str, chave: str) -> bool:
    if chave.endswith(" ") or chave.startswith(" "):
        return chave in f" {texto} "
    return re.search(r"\b" + re.escape(chave), texto) is not None


def interpretar_por_regras(pergunta: str, ctx: dict) -> dict:
    p = normalizar(pergunta)
    if any(_contem(p, k) for k in FORA_DO_ESCOPO):
        return {"acoes": [], "fora_do_escopo": True, "continuar": False, "disciplina": "", "aluno": ""}
    acoes: list[dict] = []
    usados: set[str] = set()
    for chaves, funcao, criterio in REGRAS_INTENCAO:
        if any(_contem(p, k) for k in chaves):
            chave = f"{funcao}:{criterio}"
            # quem pediu "muitas faltas" não quer também a lista geral de frequência
            if funcao == "consultar_frequencia" and "listar_alunos_em_risco:frequencia" in usados:
                continue
            if funcao == "consultar_notas" and "listar_alunos_em_risco:media" in usados:
                continue
            if funcao == "listar_alunos_em_risco" and criterio == "risco" and \
                    any(u.startswith("listar_alunos_em_risco") for u in usados):
                continue
            if funcao in ("consultar_notas", "listar_alunos_em_risco") and \
                    ("explicar_alerta:None" in usados or "sugerir_intervencao:None" in usados):
                continue
            if chave not in usados:
                usados.add(chave)
                acoes.append({"funcao": funcao, "criterio": criterio or "risco"})
    continuar = any(_contem(p, k) for k in CONTINUACAO)
    return {"acoes": acoes[:3], "continuar": continuar, "fora_do_escopo": False,
            "disciplina": "", "aluno": ""}


# ------------------------------------------------------------------ conversa
def obter_conversa(db: Session, u: Usuario, conversa_id: Optional[int]) -> Optional[Conversa]:
    if conversa_id is None:
        return None
    c = db.get(Conversa, conversa_id)
    if c is None or c.usuario_id != u.id:     # isolamento entre usuários
        return None
    return c


def listar_conversas(db: Session, u: Usuario) -> list[dict]:
    q = select(Conversa).where(Conversa.usuario_id == u.id).order_by(Conversa.atualizada_em.desc()).limit(20)
    return [{"id": c.id, "titulo": c.titulo, "atualizada_em": iso_utc(c.atualizada_em),
             "mensagens": len(c.mensagens)} for c in db.scalars(q)]


def conversa_como_dict(c: Conversa) -> dict:
    return {"id": c.id, "titulo": c.titulo,
            "mensagens": [{"pergunta": m.pergunta, "resposta": m.resposta,
                           "criada_em": iso_utc(m.criada_em)} for m in c.mensagens]}


def _resposta_base(pergunta: str, tipo: str, texto: str, **extra) -> dict:
    r = {"pergunta": pergunta, "tipo": tipo, "texto": texto, "secoes": [], "itens": [],
         "opcoes": [], "sugestoes": [], "fontes": [], "contexto": {}, "gerado_por": "regras",
         "verificacao": None, "analises_novas": 0, "aviso": AVISO, "intencao": tipo}
    r.update(extra)
    return r


def _esclarecer(pergunta: str, res, plano: dict, ctx: dict) -> dict:
    """Pergunta de volta quando o nome é ambíguo ou precisa de confirmação."""
    opcoes = [o.como_dict() for o in res.opcoes[:5]]
    if res.status == "confirmar":
        texto = f"Você quis dizer {res.escolhido.nome}?"
    elif res.tipo == "disciplina":
        texto = f"Encontrei mais de uma disciplina parecida com \"{res.termo}\". Qual delas?"
    else:
        texto = f"Encontrei mais de um estudante parecido com \"{res.termo}\". Qual deles?"
    ctx["pendente"] = {"tipo": res.tipo, "opcoes": opcoes, "plano": plano, "pergunta": pergunta}
    return _resposta_base(pergunta, "esclarecimento", texto,
                          opcoes=[{"rotulo": o["nome"] + (f" · {o['detalhe']}" if o["detalhe"] else ""),
                                   "valor": o["nome"]} for o in opcoes])


def _sugestoes(blocos: list[Bloco], pergunta: str, turmas: list[Turma], turmas_sel: list[Turma]) -> list[str]:
    """Perguntas de continuação calculadas a partir do resultado (não é lista fixa)."""
    s: list[str] = []
    funcoes = {b.funcao for b in blocos}
    com_itens = [b for b in blocos if b.matriculas]
    nomes = []
    for b in blocos:
        for it in b.itens:
            if it["aluno"].split()[0] not in nomes:
                nomes.append(it["aluno"].split()[0])
    if len(turmas_sel) > 1 and len(turmas) > 1 and blocos:
        primeira = next((it.get("disciplina") for b in blocos for it in b.itens if it.get("disciplina")),
                        turmas_sel[0].disciplina)
        s.append(f"Mostre só {primeira}")
    if com_itens and len(blocos[0].matriculas) > 1:
        if "listar_alunos_em_risco" in funcoes and not any(b.fatos.get("criterio") == "frequencia" for b in blocos):
            s.append("Quais deles também têm muitas faltas?")
        if "consultar_entregas" not in funcoes:
            s.append("E como estão as entregas deles?")
        if "sugerir_intervencao" not in funcoes:
            s.append("Sugira intervenções para esses estudantes")
    elif com_itens and len(blocos[0].matriculas) == 1 and nomes:
        if "explicar_alerta" not in funcoes:
            s.append(f"Por que {nomes[0]} tem esse alerta?")
        if "sugerir_intervencao" not in funcoes:
            s.append(f"O que posso fazer para ajudar {nomes[0]}?")
    if len(turmas_sel) == 1 and len(turmas) > 1:
        outra = next((t for t in turmas if t.id != turmas_sel[0].id), None)
        if outra and blocos:
            s.append(f"E em {outra.disciplina}?")
    p = normalizar(pergunta)
    return [x for x in s if normalizar(x) != p][:3]


def responder(db: Session, u: Usuario, pergunta: str, conversa_id: Optional[int] = None,
              turma_fixa: Optional[int] = None) -> dict:
    inicio = time.monotonic()
    pergunta = " ".join("".join(c if c.isprintable() else " " for c in pergunta).split())
    conversa = obter_conversa(db, u, conversa_id)
    if conversa is None:
        conversa = Conversa(usuario_id=u.id, titulo=pergunta[:60] or "Conversa", contexto={})
        db.add(conversa)
        db.flush()
    ctx = dict(conversa.contexto or {})
    resposta = _processar(db, u, pergunta, ctx, turma_fixa)
    resposta["conversa_id"] = conversa.id
    # o contexto guarda só ids, nomes de disciplina e as últimas perguntas
    ctx["perguntas"] = (ctx.get("perguntas", []) + [pergunta[:200]])[-config.CONTEXTO_TROCAS:]
    conversa.contexto = ctx
    conversa.atualizada_em = agora()
    db.add(MensagemConversa(conversa_id=conversa.id, pergunta=pergunta, resposta=resposta))
    db.commit()
    log.info("assistente: tipo=%s funcoes=%s gerado_por=%s ms=%d", resposta["tipo"],
             [s["funcao"] for s in resposta.get("secoes", [])], resposta["gerado_por"],
             int((time.monotonic() - inicio) * 1000))
    return resposta


def _processar(db: Session, u: Usuario, pergunta: str, ctx: dict, turma_fixa: Optional[int]) -> dict:
    turmas = turmas_autorizadas(db, u)
    if not turmas:
        return _resposta_base(pergunta, "sem_dados", "Você ainda não tem turmas vinculadas.")
    por_id = {t.id: t for t in turmas}

    # 1. Resposta a uma pergunta de esclarecimento anterior?
    escolha_disc = escolha_aluno = None
    plano: Optional[dict] = None
    pendente = ctx.pop("pendente", None)
    if pendente:
        escolhida = escolher_entre(pergunta, pendente["opcoes"])
        if escolhida:
            plano = pendente["plano"]
            if pendente["tipo"] == "disciplina":
                escolha_disc = escolhida["id"]
            else:
                escolha_aluno = escolhida["id"]
            pergunta_efetiva = pendente["pergunta"]
        else:
            pergunta_efetiva = pergunta
    else:
        pergunta_efetiva = pergunta

    # 2. Interpretação: Gemini primeiro (se disponível), regras como reserva.
    gerado_por = "regras"
    if plano is None:
        por_regras = interpretar_por_regras(pergunta_efetiva, ctx)
        plano_ia = gemini.planejar(pergunta_efetiva, {
            "disciplinas": ctx.get("disciplinas", []), "qtd_estudantes": len(ctx.get("matricula_ids", [])),
            "perguntas": ctx.get("perguntas", [])})
        if plano_ia and (plano_ia["acoes"] or plano_ia["fora_do_escopo"]):
            plano = plano_ia
            plano["continuar"] = plano["continuar"] or por_regras["continuar"]
            plano["fora_do_escopo"] = plano["fora_do_escopo"] or por_regras["fora_do_escopo"]
            gerado_por = "gemini"
        else:
            plano = por_regras

    if plano.get("fora_do_escopo"):
        return _resposta_base(
            pergunta, "fora_do_escopo",
            "Eu só consulto e explico os registros das suas turmas. Alterar notas, presenças ou "
            "dados de acesso não é feito pelo assistente: use as telas da turma.",
            sugestoes=[f"Quem precisa de acompanhamento em {turmas[0].disciplina}?"])

    # 3. Outro professor citado? Só as turmas do próprio usuário são consultáveis.
    pn = normalizar(pergunta_efetiva)
    if re.search(r"\b(professor|professora|prof)\b", pn):
        outros = db.scalars(select(Usuario).where(Usuario.perfil == "professor", Usuario.id != u.id)).all()
        rp = resolver_pessoa(pergunta_efetiva, [(o.id, o.nome.replace("Prof. ", "").replace("Profa. ", ""), "")
                                                 for o in outros], "professor")
        if rp is not None and rp.status in ("unico", "confirmar"):
            return _resposta_base(
                pergunta, "sem_permissao",
                "Só consigo consultar as turmas vinculadas a você. Turmas de outros professores "
                "ficam fora do seu acesso.")

    # 4. Disciplina citada (RapidFuzz contra as turmas do usuário).
    turmas_sel: list[Turma] = []
    if turma_fixa is not None:
        turmas_sel = [por_id[turma_fixa]] if turma_fixa in por_id else []
    elif escolha_disc is not None:
        turmas_sel = [por_id[escolha_disc]]
    else:
        texto_disc = plano.get("disciplina") or pergunta_efetiva
        res = resolver_disciplina(texto_disc, [(t.id, t.disciplina) for t in turmas])
        if res is None and plano.get("disciplina"):
            res = resolver_disciplina(pergunta_efetiva, [(t.id, t.disciplina) for t in turmas])
        if res is not None:
            if res.status == "unico":
                turmas_sel = [por_id[res.escolhido.id]]
            elif res.status in ("ambiguo", "confirmar"):
                return _esclarecer(pergunta_efetiva, res, plano, ctx)
            else:
                lista = ", ".join(t.disciplina for t in turmas)
                return _resposta_base(
                    pergunta, "sem_dados",
                    f"Não encontrei a disciplina \"{res.termo}\" entre as suas turmas ({lista}). "
                    "Só consigo consultar turmas vinculadas a você.",
                    sugestoes=[f"Quem precisa de acompanhamento em {t.disciplina}?" for t in turmas[:2]])
        if res is None and turma_fixa is None:
            termo = termo_no_fim(pergunta_efetiva)
            pessoa_no_fim = bool(termo and re.search(
                r"\b(?:aluno|aluna|estudante)\s+" + re.escape(termo) + r"$", pn))
            if (termo and not pessoa_no_fim and not plano.get("aluno")
                    and resolver_pessoa(termo, [(m.aluno_id, m.aluno.nome, m.codigo)
                                              for m in matriculas_visiveis(u, turmas)]) is None):
                lista = ", ".join(t.disciplina for t in turmas)
                return _resposta_base(
                    pergunta, "sem_dados",
                    f"Não encontrei a disciplina \"{termo}\" entre as suas turmas ({lista}). "
                    "Só consigo consultar turmas vinculadas a você.",
                    sugestoes=[f"Quem precisa de acompanhamento em {t.disciplina}?" for t in turmas[:2]])
    disciplina_citada = bool(turmas_sel)
    if not turmas_sel:
        anteriores = [por_id[i] for i in ctx.get("turma_ids", []) if i in por_id]
        turmas_sel = anteriores or turmas

    # 5. Estudante citado (RapidFuzz contra os estudantes visíveis). Um nome
    # citado é procurado em todas as turmas do usuário, a menos que a própria
    # pergunta cite a disciplina: o recorte herdado da conversa não pode
    # escolher sozinho entre duas "Anas" de turmas diferentes.
    matriculas = matriculas_visiveis(u, turmas_sel)
    alcance = matriculas_visiveis(u, turmas_sel if disciplina_citada else turmas)
    if escolha_aluno is not None:
        matriculas = [m for m in alcance if m.aluno_id == escolha_aluno]
    else:
        texto_aluno = plano.get("aluno") or pergunta_efetiva
        catalogo: dict[int, tuple[int, str, str]] = {}
        for m in alcance:
            atual = catalogo.get(m.aluno_id)
            det = f"{m.codigo} ({m.turma.disciplina})"
            catalogo[m.aluno_id] = (m.aluno_id, m.aluno.nome, det if atual is None else f"{atual[2]}, {det}")
        ra = resolver_pessoa(texto_aluno, catalogo.values())
        if ra is not None:
            if ra.status == "unico":
                matriculas = [m for m in alcance if m.aluno_id == ra.escolhido.id]
            elif ra.status in ("ambiguo", "confirmar"):
                return _esclarecer(pergunta_efetiva, ra, plano, ctx)
            else:
                return _resposta_base(pergunta, "sem_dados",
                                      "Não encontrei esse estudante entre os estudantes das suas turmas.")
        elif plano.get("aluno"):
            return _resposta_base(pergunta, "sem_dados",
                                  "Não encontrei esse estudante entre os estudantes das suas turmas.")
        elif any(k in f" {pn} " for k in PRONOME_UNICO) and len(ctx.get("aluno_ids", [])) == 1:
            matriculas = [m for m in matriculas if m.aluno_id == ctx["aluno_ids"][0]]
        elif re.search(r"\b[a-z]{1,3}\d{2}\b", pn) and not any(c in pn.split() for c in
                                                                [m.codigo.lower() for m in matriculas]):
            return _resposta_base(pergunta, "sem_dados",
                                  "Não encontrei essa matrícula entre os estudantes das suas turmas.")

    # Estudante citado: o recorte passa a ser só as turmas dele.
    if matriculas and len({m.aluno_id for m in matriculas}) == 1:
        ids_turma = {m.turma_id for m in matriculas}
        turmas_sel = [t for t in turmas if t.id in ids_turma]

    # 6. Continuação: "quais deles também..." filtra os estudantes da resposta anterior.
    if plano.get("continuar") and ctx.get("matricula_ids") and escolha_aluno is None:
        anteriores = set(ctx["matricula_ids"])
        filtradas = [m for m in matriculas if m.id in anteriores]
        if filtradas:
            matriculas = filtradas

    # 7. Funções a executar. Sem intenção reconhecida: estudante citado vira
    # análise individual; continuação reaproveita a última função.
    acoes = [a for a in plano.get("acoes", []) if a.get("funcao") in FUNCOES]
    so_um_aluno = len({m.aluno_id for m in matriculas}) == 1 and len(matriculas) < len(matriculas_visiveis(u, turmas_sel))
    if not acoes:
        if so_um_aluno:
            acoes = [{"funcao": "analisar_desempenho", "criterio": "risco"}]
        elif ctx.get("ultimas_acoes") and (plano.get("continuar") or turmas_sel != turmas):
            acoes = ctx["ultimas_acoes"]
        else:
            nomes = [t.disciplina for t in turmas]
            return _resposta_base(
                pergunta, "ajuda",
                "Não entendi o que você quer consultar. Posso falar de notas, frequência, entregas, "
                "pendências e alertas das suas turmas, explicar um alerta ou sugerir intervenções. "
                f"Suas turmas: {', '.join(nomes)}.",
                sugestoes=[f"Quem está em risco em {nomes[0]}?",
                           f"Como está a frequência em {nomes[-1]}?"])

    pares, novas = analises_atuais(db, u, matriculas)
    blocos: list[Bloco] = []
    for a in acoes[:3]:
        crit = a.get("criterio") if a.get("criterio") in CRITERIOS_VALIDOS else "risco"
        blocos.append(FUNCOES[a["funcao"]](db, u, pares=pares, turmas=turmas_sel, criterio=crit))

    # 8. Texto pelas regras e, se possível, redação do Gemini conferida.
    if len(blocos) == 1:
        texto_regras = blocos[0].texto
    else:
        texto_regras = " ".join(f"{b.titulo}: {b.texto}" for b in blocos)
    sem_dados = all(b.sem_dados for b in blocos)
    fatos = [{"funcao": b.funcao, **b.fatos, "sem_dados": b.sem_dados} for b in blocos]
    visiveis = matriculas_visiveis(u, turmas)
    nomes_no_resultado = {it["aluno"].split()[0] for b in blocos for it in b.itens}
    nomes_fora = {m.aluno.nome.split()[0] for m in visiveis} - nomes_no_resultado
    texto, situacao = gemini.redigir(pergunta_efetiva, fatos, texto_regras, nomes_fora, sem_dados)
    if texto:
        gerado_por = "gemini"
    else:
        texto = texto_regras
        if gerado_por == "gemini":
            gerado_por = "gemini+regras"

    # 9. Contexto para a próxima pergunta.
    ctx["turma_ids"] = [t.id for t in turmas_sel] if turmas_sel != turmas else []
    ctx["disciplinas"] = [t.disciplina for t in turmas_sel]
    ids = [i for b in blocos for i in b.matriculas]
    if ids:
        ctx["matricula_ids"] = list(dict.fromkeys(ids))[:60]
        ctx["aluno_ids"] = list(dict.fromkeys(m.aluno_id for m in matriculas if m.id in set(ids)))[:60]
    ctx["ultimas_acoes"] = acoes[:3]

    regras = set().union(*(b.regras for b in blocos))
    itens = [it for b in blocos for it in b.itens]
    return _resposta_base(
        pergunta, "sem_dados" if sem_dados else "resposta", texto,
        secoes=[b.como_dict() for b in blocos], itens=itens,
        sugestoes=_sugestoes(blocos, pergunta, turmas, turmas_sel),
        fontes=fontes(regras, turmas_sel),
        contexto={"disciplinas": [t.disciplina for t in turmas_sel],
                  "estudantes": len({m.aluno_id for m in matriculas}),
                  "continuacao": bool(plano.get("continuar") and ctx.get("matricula_ids"))},
        gerado_por=gerado_por, verificacao=None if situacao in ("aprovada", "desativado") else situacao,
        analises_novas=novas, intencao=blocos[0].funcao)
