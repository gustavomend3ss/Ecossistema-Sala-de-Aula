"""Coordena a análise de uma matrícula (RF04, RF05, RF06 e regra R5).

Caminho: ler cópia fixa dos registros → motor → conferir se nada mudou →
gravar análise (nunca sobrescreve a anterior) → síntese opcional.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Analise, Matricula, Usuario, iso_utc
from ..motor import Criterios, analisar, montar_motivo
from . import sintese as sintese_mod
from .registros import fatos_como_dict, montar_fatos


def criterios_da_turma(m: Matricula) -> Criterios:
    c = m.turma.criterio
    return Criterios(versao=c.versao, media_minima=c.media_minima,
                     frequencia_minima=c.frequencia_minima,
                     atrasos_maximos=c.atrasos_maximos)


def ultima_analise(db: Session, matricula_id: int) -> Analise | None:
    return db.scalar(
        select(Analise).where(Analise.matricula_id == matricula_id)
        .order_by(Analise.criado_em.desc(), Analise.id.desc()).limit(1))


def esta_desatualizada(a: Analise, m: Matricula) -> bool:
    return (a.versao_registros != m.versao_registros
            or a.versao_criterios != m.turma.criterio.versao)


def executar_analise(db: Session, m: Matricula, solicitante: Usuario,
                     com_sintese: bool = True) -> Analise:
    versao_inicial = m.versao_registros
    fatos = montar_fatos(db, m)
    criterios = criterios_da_turma(m)

    resultado = analisar(fatos, criterios)
    motivo = montar_motivo(resultado, criterios)

    # A API nunca mostra resultado velho como atual: se algum registro mudou
    # durante o processamento, pede uma nova análise.
    db.refresh(m)
    if m.versao_registros != versao_inicial:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Os registros mudaram durante a análise. Solicite novamente.")

    acionadas = [a.como_dict() for a in resultado.acionadas]
    regras = list(resultado.regras)

    # R5: registro ou critério atualizado desde a análise anterior
    anterior = ultima_analise(db, m.id)
    if anterior is not None and (anterior.versao_registros != m.versao_registros
                                 or anterior.versao_criterios != criterios.versao):
        acionadas.append({
            "regra": "R5", "corpo": ["registro_ou_criterio_atualizado"],
            "cabeca": "nova_analise",
            "evidencia": {
                "analise_anterior_id": anterior.id,
                "versao_registros_anterior": anterior.versao_registros,
                "versao_registros_atual": m.versao_registros,
                "criterios_anteriores": anterior.versao_criterios,
                "criterios_atuais": criterios.versao,
            }})
        regras.append("R5")

    analise = Analise(
        matricula_id=m.id,
        solicitado_por_id=solicitante.id,
        criterio_id=m.turma.criterio_id,
        versao_registros=m.versao_registros,
        versao_criterios=criterios.versao,
        media=resultado.media,
        frequencia=resultado.frequencia,
        presencas=resultado.presencas,
        unidades_consideradas=resultado.unidades_consideradas,
        atividades_vencidas=resultado.atividades_vencidas,
        atividades_sem_entrega=resultado.atividades_sem_entrega,
        certeza=resultado.certeza,
        prioridade=resultado.prioridade,
        regras=regras,
        acionadas=acionadas,
        pendencias=[p.como_dict() for p in resultado.pendencias],
        fatos=fatos_como_dict(fatos),
        motivo=motivo,
    )

    # Síntese auxiliar: só recebe o que o motor calculou (sem nome do aluno).
    fatos_motor = {
        "versao_criterios": criterios.versao,
        "media": resultado.media,
        "frequencia": resultado.frequencia,
        "media_minima": criterios.media_minima,
        "frequencia_minima": criterios.frequencia_minima,
        "presencas": resultado.presencas,
        "unidades_consideradas": resultado.unidades_consideradas,
        "atividades_vencidas": resultado.atividades_vencidas,
        "atividades_sem_entrega": resultado.atividades_sem_entrega,
        "atrasos_maximos": criterios.atrasos_maximos,
        "grau_de_certeza": resultado.certeza,
        "regras": [r for r in resultado.regras],
        "pendencias": [p.como_dict() for p in resultado.pendencias],
        "motivo_estruturado": motivo,
    }
    if com_sintese:
        s = sintese_mod.gerar_sintese(fatos_motor, sintese_mod.chamador_padrao)
        analise.sintese = s.texto
        status_txt = s.status if not s.motivo else f"{s.status}: {s.motivo}"
        analise.sintese_status = status_txt[:300]
    else:
        analise.sintese_status = "nao_solicitada"

    db.add(analise)
    db.commit()
    db.refresh(analise)
    return analise


def analise_como_dict(a: Analise, m: Matricula) -> dict:
    return {
        "id": a.id,
        "matricula_id": a.matricula_id,
        "codigo": m.codigo,
        "aluno": m.aluno.nome,
        "criado_em": iso_utc(a.criado_em),
        "solicitado_por": a.solicitado_por.nome,
        "versao_registros": a.versao_registros,
        "versao_criterios": a.versao_criterios,
        "desatualizada": esta_desatualizada(a, m),
        "media": a.media,
        "frequencia": a.frequencia,
        "presencas": a.presencas,
        "unidades_consideradas": a.unidades_consideradas,
        "atividades_vencidas": a.atividades_vencidas,
        "atividades_sem_entrega": a.atividades_sem_entrega,
        "certeza": a.certeza,
        "prioridade": a.prioridade,
        "regras": a.regras,
        "acionadas": a.acionadas,
        "pendencias": a.pendencias,
        "motivo": a.motivo,
        "fatos": a.fatos,
        "sintese": a.sintese,
        "sintese_status": a.sintese_status,
        "criterios": {
            "versao": a.versao_criterios,
            "media_minima": a.criterio.media_minima,
            "frequencia_minima": a.criterio.frequencia_minima,
            "atrasos_maximos": a.criterio.atrasos_maximos,
        },
        "revisoes": [
            {"id": r.id, "autor": r.autor.nome, "decisao": r.decisao,
             "observacao": r.observacao, "criado_em": iso_utc(r.criado_em)}
            for r in a.revisoes],
    }
