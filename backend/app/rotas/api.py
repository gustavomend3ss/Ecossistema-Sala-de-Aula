"""Rotas REST. As do Quadro 4 do Bloco 2 estão marcadas com [Q4]."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from .. import config, seguranca
from ..esquemas import (AtividadeEntrada, ConferenciaEntrada, EntregaEntrada,
                        LoginEntrada, MensagemEntrada, NotaEntrada, PerguntaEntrada,
                        PresencaEntrada, RespostaEntrada, RevisaoEntrada)
from ..models import (Analise, Atividade, Aula, Avaliacao, Entrega, Matricula, PedidoConferencia,
                      Revisao, Turma, Usuario, VinculoProfessorTurma,
                      agora, iso_utc)
from ..motor import Criterios, analisar
from ..seguranca import (ACESSO_NEGADO, conferir_senha, criar_token,
                         exigir_professor, exigir_turma, obter_matricula,
                         usuario_atual)
from ..servicos import assistente, conversa
from ..servicos.analises import (analise_como_dict, esta_desatualizada,
                                 executar_analise, ultima_analise)
from ..servicos.registros import (historico_alteracoes, montar_fatos,
                                  registros_da_matricula, salvar_entrega,
                                  salvar_nota, salvar_presenca, situacao_entrega)

router = APIRouter()


def _usuario_dict(u: Usuario) -> dict:
    return {"id": u.id, "nome": u.nome, "login": u.login, "perfil": u.perfil}


def _criterios(t: Turma) -> Criterios:
    c = t.criterio
    return Criterios(c.versao, c.media_minima, c.frequencia_minima, c.atrasos_maximos)


def _indicadores(db: Session, m: Matricula) -> dict:
    """Indicadores ao vivo, só para exibição. Não grava análise."""
    r = analisar(montar_fatos(db, m), _criterios(m.turma))
    return {"media": r.media, "frequencia": r.frequencia,
            "presencas": r.presencas, "unidades_consideradas": r.unidades_consideradas,
            "atividades_vencidas": r.atividades_vencidas,
            "atividades_sem_entrega": r.atividades_sem_entrega,
            "taxa_entrega": r.taxa_entrega,
            "completude": "completa" if not r.pendencias else "parcial",
            "pendencias": [p.como_dict() for p in r.pendencias]}


# --------------------------------------------------------------- sessões
@router.post("/sessoes", tags=["sessões"])                     # [Q4]
def entrar(dados: LoginEntrada, request: Request, db: Session = Depends(get_db)):
    # Na Vercel, o endereço real vem em x-forwarded-for, preenchido pela
    # própria plataforma; fora dela, vale o endereço da conexão.
    encaminhado = request.headers.get("x-forwarded-for", "") if config.NA_VERCEL else ""
    ip = encaminhado.split(",")[0].strip() or (request.client.host if request.client else "?")
    espera = seguranca.segundos_bloqueado(dados.login, ip)
    if espera:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Muitas tentativas. Tente de novo em {max(1, espera // 60)} min.",
            headers={"Retry-After": str(espera)})
    u = db.scalar(select(Usuario).where(Usuario.login == dados.login.strip().lower()))
    if u is None or not conferir_senha(dados.senha, u.senha_hash):
        seguranca.registrar_falha(dados.login, ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário ou senha incorretos.")
    seguranca.limpar_falhas(dados.login, ip)
    token, expira = criar_token(u)
    return {"token": token, "expira_em": expira.isoformat(), "usuario": _usuario_dict(u)}


@router.delete("/sessoes", status_code=204, tags=["sessões"])
def sair(u: Usuario = Depends(usuario_atual)):
    # O token não fica no servidor: sair é descartá-lo no aplicativo.
    return None


@router.get("/me", tags=["sessões"])
def eu(u: Usuario = Depends(usuario_atual)):
    return _usuario_dict(u)


# ---------------------------------------------------------------- turmas
@router.get("/turmas", tags=["turmas"])                        # [Q4]
def listar_turmas(u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    if u.perfil == "professor":
        turmas = db.scalars(
            select(Turma).join(VinculoProfessorTurma)
            .where(VinculoProfessorTurma.professor_id == u.id).order_by(Turma.disciplina))
        saida = []
        for t in turmas:
            alertas = pendentes = desatualizadas = 0
            for m in t.matriculas:
                a = ultima_analise(db, m.id)
                if a is None or esta_desatualizada(a, m):
                    desatualizadas += 1
                    continue
                if a.prioridade in ("prioridade_alta", "alerta_media", "alerta_frequencia",
                                    "alerta_entregas"):
                    alertas += 1
                if a.pendencias:
                    pendentes += 1
            conferencias = db.scalar(
                select(func.count(PedidoConferencia.id)).join(Matricula)
                .where(Matricula.turma_id == t.id, PedidoConferencia.status == "aberto"))
            saida.append({
                "id": t.id, "disciplina": t.disciplina, "periodo": t.periodo,
                "descricao": t.descricao, "estudantes": len(t.matriculas),
                "criterios": t.criterio.versao, "alertas": alertas,
                "pendencias": pendentes, "sem_analise_atual": desatualizadas,
                "conferencias_abertas": conferencias})
        return saida

    mats = db.scalars(select(Matricula).where(Matricula.aluno_id == u.id))
    return [{"id": m.turma.id, "disciplina": m.turma.disciplina,
             "periodo": m.turma.periodo, "descricao": m.turma.descricao,
             "matricula_id": m.id, "codigo": m.codigo} for m in mats]


@router.get("/turmas/{turma_id}", tags=["turmas"])
def detalhar_turma(turma_id: int, u: Usuario = Depends(usuario_atual),
                   db: Session = Depends(get_db)):
    exigir_turma(db, u, turma_id)
    t = db.get(Turma, turma_id)
    estudantes = []
    for m in sorted(t.matriculas, key=lambda x: x.codigo):
        reg = registros_da_matricula(db, m)
        a = ultima_analise(db, m.id)
        abertas = db.scalar(select(func.count(PedidoConferencia.id)).where(
            PedidoConferencia.matricula_id == m.id, PedidoConferencia.status == "aberto"))
        estudantes.append({
            "matricula_id": m.id, "codigo": m.codigo, "aluno": m.aluno.nome,
            "versao_registros": m.versao_registros,
            "notas": {str(x["avaliacao_id"]): x["valor"] for x in reg["avaliacoes"]},
            "presencas_por_aula": {str(x["aula_id"]): x["presente"] for x in reg["aulas"]},
            "entregas_por_atividade": {str(x["atividade_id"]): x["situacao"] for x in reg["atividades"]},
            **_indicadores(db, m),
            "acompanhamento": None if a is None else {
                "analise_id": a.id, "prioridade": a.prioridade,
                "regras": a.regras, "desatualizada": esta_desatualizada(a, m),
                "criado_em": iso_utc(a.criado_em)},
            "conferencias_abertas": abertas,
        })
    c = t.criterio
    return {
        "id": t.id, "disciplina": t.disciplina, "periodo": t.periodo,
        "descricao": t.descricao,
        "criterios": {"versao": c.versao, "descricao": c.descricao,
                      "media_minima": c.media_minima,
                      "frequencia_minima": c.frequencia_minima,
                      "atrasos_maximos": c.atrasos_maximos},
        "avaliacoes": [{"id": a.id, "nome": a.nome, "peso": a.peso,
                        "nota_maxima": a.nota_maxima, "obrigatoria": a.obrigatoria}
                       for a in t.avaliacoes],
        "aulas": [{"id": a.id, "ordem": a.ordem, "data": a.data, "tema": a.tema,
                   "unidades": a.unidades} for a in t.aulas],
        "atividades": [_atividade_resumo(db, a) for a in t.atividades],
        "estudantes": estudantes,
    }


def _atividade_resumo(db: Session, a: Atividade) -> dict:
    """Radar de entregas de uma atividade: quantos entregaram, no prazo ou não."""
    hoje = config.hoje()
    entregas = {e.matricula_id: e.entregue_em for e in
                db.scalars(select(Entrega).where(Entrega.atividade_id == a.id))}
    cont = {"entregue": 0, "entregue_atraso": 0, "atrasada": 0, "aberta": 0}
    for m in a.turma.matriculas:
        cont[situacao_entrega(a.prazo, entregas.get(m.id), hoje)] += 1
    return {"id": a.id, "titulo": a.titulo, "descricao": a.descricao, "prazo": a.prazo,
            "vencida": a.prazo < hoje.isoformat(),
            "contagem": cont, "total": len(a.turma.matriculas)}


@router.get("/turmas/{turma_id}/atividades", tags=["atividades"])
def listar_atividades(turma_id: int, u: Usuario = Depends(exigir_professor),
                      db: Session = Depends(get_db)):
    exigir_turma(db, u, turma_id)
    t = db.get(Turma, turma_id)
    return [_atividade_resumo(db, a) for a in t.atividades]


@router.post("/turmas/{turma_id}/atividades", status_code=201, tags=["atividades"])
def criar_atividade(turma_id: int, dados: AtividadeEntrada,
                    u: Usuario = Depends(exigir_professor), db: Session = Depends(get_db)):
    exigir_turma(db, u, turma_id)
    if len(dados.titulo) < 3:
        raise HTTPException(422, "O título precisa de pelo menos 3 caracteres úteis.")
    a = Atividade(turma_id=turma_id, titulo=dados.titulo, descricao=dados.descricao,
                  prazo=dados.prazo.isoformat())
    db.add(a)
    db.commit()
    db.refresh(a)
    return _atividade_resumo(db, a)


@router.put("/matriculas/{matricula_id}/entregas/{atividade_id}", tags=["atividades"])
def marcar_entrega(matricula_id: int, atividade_id: int, dados: EntregaEntrada,
                   u: Usuario = Depends(exigir_professor), db: Session = Depends(get_db)):
    m = obter_matricula(db, u, matricula_id)
    salvar_entrega(db, m, atividade_id, dados.entregue, u)
    return {**registros_da_matricula(db, m), "indicadores": _indicadores(db, m)}


@router.post("/turmas/{turma_id}/analises", tags=["análises"])
def analisar_turma(turma_id: int, u: Usuario = Depends(exigir_professor),
                   db: Session = Depends(get_db)):
    exigir_turma(db, u, turma_id)
    t = db.get(Turma, turma_id)
    return [analise_como_dict(executar_analise(db, m, u), m)
            for m in sorted(t.matriculas, key=lambda x: x.codigo)]


@router.post("/assistente/mensagens", tags=["assistente"])
def conversar(dados: MensagemEntrada, u: Usuario = Depends(exigir_professor),
              db: Session = Depends(get_db)):
    """Assistente com contexto: a turma e os estudantes vêm da própria pergunta
    (RapidFuzz) ou da conversa. Uma conversa de outro usuário é tratada como
    inexistente."""
    if dados.conversa_id is not None and conversa.obter_conversa(db, u, dados.conversa_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada.")
    return conversa.responder(db, u, dados.pergunta, dados.conversa_id)


@router.get("/assistente/conversas", tags=["assistente"])
def conversas(u: Usuario = Depends(exigir_professor), db: Session = Depends(get_db)):
    return conversa.listar_conversas(db, u)


@router.get("/assistente/conversas/{conversa_id}", tags=["assistente"])
def ver_conversa(conversa_id: int, u: Usuario = Depends(exigir_professor),
                 db: Session = Depends(get_db)):
    c = conversa.obter_conversa(db, u, conversa_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada.")
    return conversa.conversa_como_dict(c)


@router.post("/turmas/{turma_id}/assistente", tags=["assistente"])
def perguntar(turma_id: int, dados: PerguntaEntrada,
              u: Usuario = Depends(exigir_professor), db: Session = Depends(get_db)):
    exigir_turma(db, u, turma_id)
    return assistente.responder(db, db.get(Turma, turma_id), u, dados.pergunta)


# ------------------------------------------------------------ matrículas
@router.get("/matriculas/{matricula_id}/registros", tags=["registros"])   # [Q4]
def registros(matricula_id: int, u: Usuario = Depends(usuario_atual),
              db: Session = Depends(get_db)):
    m = obter_matricula(db, u, matricula_id)
    return {**registros_da_matricula(db, m), "indicadores": _indicadores(db, m)}


@router.put("/matriculas/{matricula_id}/notas/{avaliacao_id}", tags=["registros"])  # [Q4]
def corrigir_nota(matricula_id: int, avaliacao_id: int, dados: NotaEntrada,
                  u: Usuario = Depends(exigir_professor), db: Session = Depends(get_db)):
    m = obter_matricula(db, u, matricula_id)
    salvar_nota(db, m, avaliacao_id, dados.valor, u)
    return {**registros_da_matricula(db, m), "indicadores": _indicadores(db, m)}


@router.put("/matriculas/{matricula_id}/presencas/{aula_id}", tags=["registros"])   # [Q4]
def corrigir_presenca(matricula_id: int, aula_id: int, dados: PresencaEntrada,
                      u: Usuario = Depends(exigir_professor), db: Session = Depends(get_db)):
    m = obter_matricula(db, u, matricula_id)
    salvar_presenca(db, m, aula_id, dados.presente, u)
    return {**registros_da_matricula(db, m), "indicadores": _indicadores(db, m)}


@router.get("/matriculas/{matricula_id}/historico", tags=["registros"])
def historico(matricula_id: int, u: Usuario = Depends(exigir_professor),
              db: Session = Depends(get_db)):
    m = obter_matricula(db, u, matricula_id)
    return historico_alteracoes(db, m)


@router.post("/matriculas/{matricula_id}/analises", status_code=201, tags=["análises"])  # [Q4]
def nova_analise(matricula_id: int, u: Usuario = Depends(exigir_professor),
                 db: Session = Depends(get_db)):
    m = obter_matricula(db, u, matricula_id)
    return analise_como_dict(executar_analise(db, m, u), m)


@router.get("/matriculas/{matricula_id}/analises", tags=["análises"])   # [Q4]
def listar_analises(matricula_id: int, u: Usuario = Depends(exigir_professor),
                    db: Session = Depends(get_db)):
    m = obter_matricula(db, u, matricula_id)
    analises = db.scalars(select(Analise).where(Analise.matricula_id == m.id)
                          .order_by(Analise.criado_em.desc(), Analise.id.desc()))
    return [analise_como_dict(a, m) for a in analises]


@router.post("/analises/{analise_id}/revisoes", status_code=201, tags=["análises"])   # [Q4]
def revisar(analise_id: int, dados: RevisaoEntrada,
            u: Usuario = Depends(exigir_professor), db: Session = Depends(get_db)):
    a = db.get(Analise, analise_id)
    if a is None:
        raise ACESSO_NEGADO
    m = obter_matricula(db, u, a.matricula_id)
    db.add(Revisao(analise_id=a.id, autor_id=u.id, decisao=dados.decisao,
                   observacao=dados.observacao.strip()))
    db.commit()
    db.refresh(a)
    return analise_como_dict(a, m)


# ---------------------------------------------------- pedidos de conferência
def _conferencia_dict(p: PedidoConferencia) -> dict:
    return {"id": p.id, "matricula_id": p.matricula_id, "autor": p.autor.nome,
            "referencia": p.referencia, "referencia_rotulo": p.referencia_rotulo,
            "mensagem": p.mensagem, "status": p.status, "resposta": p.resposta,
            "criado_em": iso_utc(p.criado_em),
            "respondido_em": iso_utc(p.respondido_em)}


def _rotulo_da_referencia(db: Session, m: Matricula, referencia: str) -> str:
    """Nome legível do registro citado; 404 se ele não for da turma da matrícula."""
    if referencia == "geral":
        return "Registro geral da matrícula"
    tipo, ident = referencia.split(":")
    modelo = {"avaliacao": Avaliacao, "aula": Aula, "atividade": Atividade}[tipo]
    obj = db.get(modelo, int(ident))
    if obj is None or obj.turma_id != m.turma_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "O registro indicado não pertence a esta matrícula.")
    return {"avaliacao": lambda o: o.nome,
            "aula": lambda o: f"Aula {o.ordem} ({o.data})",
            "atividade": lambda o: f"Entrega: {o.titulo}"}[tipo](obj)


def _pedido_do_aluno(db: Session, u: Usuario, pedido_id: int) -> PedidoConferencia:
    """Pedido que o aluno pode mudar: dele e ainda sem resposta do professor.
    Pedido de outra pessoa = 404 (não revela que existe)."""
    if u.perfil != "aluno":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Só o aluno que fez o pedido pode alterá-lo ou removê-lo.")
    p = db.get(PedidoConferencia, pedido_id)
    if p is None or p.autor_id != u.id:
        raise ACESSO_NEGADO
    obter_matricula(db, u, p.matricula_id)
    if p.status != "aberto":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "O professor já respondeu este pedido: ele não pode mais ser alterado.")
    return p


@router.post("/matriculas/{matricula_id}/conferencias", status_code=201,
             tags=["conferências"])                                   # [Q4]
def pedir_conferencia(matricula_id: int, dados: ConferenciaEntrada,
                      u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    m = obter_matricula(db, u, matricula_id)
    if u.perfil != "aluno":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "O pedido de conferência é feito pelo aluno.")
    rotulo = _rotulo_da_referencia(db, m, dados.referencia)
    p = PedidoConferencia(matricula_id=m.id, autor_id=u.id, referencia=dados.referencia,
                          referencia_rotulo=rotulo, mensagem=dados.mensagem.strip())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _conferencia_dict(p)


@router.get("/matriculas/{matricula_id}/conferencias", tags=["conferências"])
def listar_conferencias(matricula_id: int, u: Usuario = Depends(usuario_atual),
                        db: Session = Depends(get_db)):
    m = obter_matricula(db, u, matricula_id)
    itens = db.scalars(select(PedidoConferencia)
                       .where(PedidoConferencia.matricula_id == m.id)
                       .order_by(PedidoConferencia.criado_em.desc()))
    return [_conferencia_dict(p) for p in itens]


@router.put("/conferencias/{pedido_id}", tags=["conferências"])
def editar_conferencia(pedido_id: int, dados: ConferenciaEntrada,
                       u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    p = _pedido_do_aluno(db, u, pedido_id)
    m = db.get(Matricula, p.matricula_id)
    p.referencia_rotulo = _rotulo_da_referencia(db, m, dados.referencia)
    p.referencia = dados.referencia
    p.mensagem = dados.mensagem.strip()
    db.commit()
    db.refresh(p)
    return _conferencia_dict(p)


@router.delete("/conferencias/{pedido_id}", status_code=204, tags=["conferências"])
def remover_conferencia(pedido_id: int, u: Usuario = Depends(usuario_atual),
                        db: Session = Depends(get_db)):
    p = _pedido_do_aluno(db, u, pedido_id)
    db.delete(p)
    db.commit()


@router.post("/conferencias/{pedido_id}/resposta", tags=["conferências"])
def responder_conferencia(pedido_id: int, dados: RespostaEntrada,
                          u: Usuario = Depends(exigir_professor),
                          db: Session = Depends(get_db)):
    p = db.get(PedidoConferencia, pedido_id)
    if p is None:
        raise ACESSO_NEGADO
    obter_matricula(db, u, p.matricula_id)
    p.resposta = dados.resposta.strip()
    p.status = "respondido"
    p.respondido_em = agora()
    db.commit()
    return _conferencia_dict(p)


# ------------------------------------------------------------- área do aluno
@router.get("/aluno/desempenho", tags=["aluno"])
def meu_desempenho(u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    if u.perfil != "aluno":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Área exclusiva do aluno.")
    mats = db.scalars(select(Matricula).where(Matricula.aluno_id == u.id))
    return [{**registros_da_matricula(db, m), "indicadores": _indicadores(db, m)}
            for m in mats]
