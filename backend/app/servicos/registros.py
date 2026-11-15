"""Leitura e correção de notas e presenças (RF03)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (Aula, Avaliacao, HistoricoAlteracao, Matricula, Nota,
                      Presenca, Usuario, agora)
from ..motor import Fatos, NotaFato, PresencaFato, fmt_num


def _notas_por_avaliacao(db: Session, matricula_id: int) -> dict[int, Nota]:
    notas = db.scalars(select(Nota).where(Nota.matricula_id == matricula_id))
    return {n.avaliacao_id: n for n in notas}


def _presencas_por_aula(db: Session, matricula_id: int) -> dict[int, Presenca]:
    pres = db.scalars(select(Presenca).where(Presenca.matricula_id == matricula_id))
    return {p.aula_id: p for p in pres}


def montar_fatos(db: Session, m: Matricula) -> Fatos:
    """Cópia fixa dos registros da matrícula naquele momento."""
    notas = _notas_por_avaliacao(db, m.id)
    pres = _presencas_por_aula(db, m.id)
    return Fatos(
        matricula=m.codigo,
        versao_registros=m.versao_registros,
        notas=tuple(
            NotaFato(
                avaliacao=a.nome, peso=a.peso, obrigatoria=a.obrigatoria,
                valor=notas[a.id].valor if a.id in notas else None,
                nota_maxima=a.nota_maxima)
            for a in m.turma.avaliacoes),
        presencas=tuple(
            PresencaFato(
                aula=f"Aula {a.ordem} ({a.data})", unidades=a.unidades,
                presente=pres[a.id].presente if a.id in pres else None)
            for a in m.turma.aulas),
    )


def fatos_como_dict(f: Fatos) -> dict:
    return {
        "matricula": f.matricula,
        "versao_registros": f.versao_registros,
        "notas": [{"avaliacao": n.avaliacao, "peso": n.peso, "obrigatoria": n.obrigatoria,
                   "valor": n.valor, "nota_maxima": n.nota_maxima} for n in f.notas],
        "presencas": [{"aula": p.aula, "unidades": p.unidades, "presente": p.presente}
                      for p in f.presencas],
    }


def registros_da_matricula(db: Session, m: Matricula) -> dict:
    notas = _notas_por_avaliacao(db, m.id)
    pres = _presencas_por_aula(db, m.id)
    return {
        "matricula_id": m.id,
        "codigo": m.codigo,
        "aluno": m.aluno.nome,
        "turma_id": m.turma_id,
        "disciplina": m.turma.disciplina,
        "periodo": m.turma.periodo,
        "versao_registros": m.versao_registros,
        "avaliacoes": [
            {"avaliacao_id": a.id, "nome": a.nome, "peso": a.peso,
             "nota_maxima": a.nota_maxima, "obrigatoria": a.obrigatoria,
             "valor": notas[a.id].valor if a.id in notas else None,
             "versao": notas[a.id].versao if a.id in notas else 0}
            for a in m.turma.avaliacoes],
        "aulas": [
            {"aula_id": a.id, "ordem": a.ordem, "data": a.data, "tema": a.tema,
             "unidades": a.unidades,
             "presente": pres[a.id].presente if a.id in pres else None}
            for a in m.turma.aulas],
    }


def _registrar_historico(db, m, autor, tipo, referencia, anterior, novo):
    db.add(HistoricoAlteracao(
        matricula_id=m.id, autor_id=autor.id, tipo=tipo, referencia=referencia,
        valor_anterior=anterior, valor_novo=novo))


def salvar_nota(db: Session, m: Matricula, avaliacao_id: int, valor: float,
                autor: Usuario) -> None:
    av = db.get(Avaliacao, avaliacao_id)
    if av is None or av.turma_id != m.turma_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Avaliação não pertence à turma desta matrícula.")
    if not (0 <= valor <= av.nota_maxima):   # T07
        raise HTTPException(
            422,
            f"A nota {fmt_num(valor)} está fora da escala de 0 a "
            f"{fmt_num(av.nota_maxima)}. Nada foi salvo.")

    nota = db.scalar(select(Nota).where(Nota.matricula_id == m.id,
                                        Nota.avaliacao_id == avaliacao_id))
    anterior = None
    if nota is None:
        nota = Nota(matricula_id=m.id, avaliacao_id=avaliacao_id, valor=valor, versao=1)
        db.add(nota)
    else:
        if nota.valor == valor:
            return
        anterior = None if nota.valor is None else fmt_num(nota.valor)
        nota.valor = valor
        nota.versao += 1
        nota.atualizado_em = agora()
    m.versao_registros += 1
    _registrar_historico(db, m, autor, "nota", av.nome, anterior, fmt_num(valor))
    db.commit()


def salvar_presenca(db: Session, m: Matricula, aula_id: int, presente: bool,
                    autor: Usuario) -> None:
    aula = db.get(Aula, aula_id)
    if aula is None or aula.turma_id != m.turma_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Aula não pertence à turma desta matrícula.")
    p = db.scalar(select(Presenca).where(Presenca.matricula_id == m.id,
                                         Presenca.aula_id == aula_id))
    rotulo = lambda v: "presente" if v else "falta"   # noqa: E731
    anterior = None
    if p is None:
        p = Presenca(matricula_id=m.id, aula_id=aula_id, presente=presente, versao=1)
        db.add(p)
    else:
        if p.presente == presente:
            return
        anterior = rotulo(p.presente)
        p.presente = presente
        p.versao += 1
        p.atualizado_em = agora()
    m.versao_registros += 1
    _registrar_historico(db, m, autor, "presenca", f"Aula {aula.ordem} ({aula.data})",
                         anterior, rotulo(presente))
    db.commit()


def historico_alteracoes(db: Session, m: Matricula) -> list[dict]:
    itens = db.scalars(
        select(HistoricoAlteracao)
        .where(HistoricoAlteracao.matricula_id == m.id)
        .order_by(HistoricoAlteracao.criado_em.desc(), HistoricoAlteracao.id.desc()))
    return [{"id": h.id, "tipo": h.tipo, "referencia": h.referencia,
             "valor_anterior": h.valor_anterior, "valor_novo": h.valor_novo,
             "autor": h.autor.nome, "criado_em": h.criado_em.isoformat()}
            for h in itens]
