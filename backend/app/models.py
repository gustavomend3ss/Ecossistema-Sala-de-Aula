"""Modelo de dados (seção 4.5 do documento do Bloco 2).

Entidades: usuário, turma, vínculo professor-turma, matrícula, avaliação,
nota, aula, presença, critério, análise, revisão e pedido de conferência.
No Bloco 3 entraram atividade e entrega (dor apontada no Bloco 1) e o
histórico de alterações dos registros.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (JSON, Boolean, CheckConstraint, DateTime, Float,
                        ForeignKey, Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuario"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(60), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    perfil: Mapped[str] = mapped_column(String(20))   # professor | aluno
    senha_hash: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        CheckConstraint("perfil in ('professor','aluno')", name="ck_perfil"),)


class Criterio(Base):
    """Perfil de critérios com versão (ex.: DEMO-v1). Troca sem mexer no código."""
    __tablename__ = "criterio"
    id: Mapped[int] = mapped_column(primary_key=True)
    versao: Mapped[str] = mapped_column(String(30), unique=True)
    descricao: Mapped[str] = mapped_column(String(200), default="")
    media_minima: Mapped[float] = mapped_column(Float)
    frequencia_minima: Mapped[float] = mapped_column(Float)
    # Atividades vencidas sem entrega toleradas antes da regra R6
    atrasos_maximos: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        CheckConstraint("media_minima >= 0 and media_minima <= 10", name="ck_media_min"),
        CheckConstraint("frequencia_minima >= 0 and frequencia_minima <= 100", name="ck_freq_min"),
    )


class Turma(Base):
    __tablename__ = "turma"
    id: Mapped[int] = mapped_column(primary_key=True)
    disciplina: Mapped[str] = mapped_column(String(120))
    periodo: Mapped[str] = mapped_column(String(20))
    descricao: Mapped[str] = mapped_column(String(120), default="")
    criterio_id: Mapped[int] = mapped_column(ForeignKey("criterio.id"))
    criterio: Mapped[Criterio] = relationship()
    matriculas: Mapped[list["Matricula"]] = relationship(back_populates="turma")
    avaliacoes: Mapped[list["Avaliacao"]] = relationship(
        back_populates="turma", order_by="Avaliacao.ordem")
    aulas: Mapped[list["Aula"]] = relationship(
        back_populates="turma", order_by="Aula.ordem")
    atividades: Mapped[list["Atividade"]] = relationship(
        back_populates="turma", order_by="Atividade.prazo")


class VinculoProfessorTurma(Base):
    __tablename__ = "vinculo_professor_turma"
    id: Mapped[int] = mapped_column(primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    turma_id: Mapped[int] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"))
    __table_args__ = (UniqueConstraint("professor_id", "turma_id"),)


class Matricula(Base):
    __tablename__ = "matricula"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20))           # A01, A02...
    turma_id: Mapped[int] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"))
    aluno_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    # Cresce a cada correção de nota ou presença. A análise guarda a versão
    # que usou; se for diferente da atual, a análise está desatualizada (R5).
    versao_registros: Mapped[int] = mapped_column(Integer, default=1)
    turma: Mapped[Turma] = relationship(back_populates="matriculas")
    aluno: Mapped[Usuario] = relationship()
    __table_args__ = (UniqueConstraint("turma_id", "aluno_id"),
                      UniqueConstraint("turma_id", "codigo"))


class Avaliacao(Base):
    __tablename__ = "avaliacao"
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"))
    nome: Mapped[str] = mapped_column(String(80))
    peso: Mapped[float] = mapped_column(Float, default=1.0)
    nota_maxima: Mapped[float] = mapped_column(Float, default=10.0)
    obrigatoria: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    turma: Mapped[Turma] = relationship(back_populates="avaliacoes")
    __table_args__ = (CheckConstraint("peso > 0", name="ck_peso"),
                      CheckConstraint("nota_maxima > 0", name="ck_nota_max"))


class Nota(Base):
    __tablename__ = "nota"
    id: Mapped[int] = mapped_column(primary_key=True)
    matricula_id: Mapped[int] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"))
    avaliacao_id: Mapped[int] = mapped_column(ForeignKey("avaliacao.id", ondelete="CASCADE"))
    # Valor opcional: nota ainda não lançada fica nula, nunca zero.
    valor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    versao: Mapped[int] = mapped_column(Integer, default=1)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    __table_args__ = (UniqueConstraint("matricula_id", "avaliacao_id"),
                      CheckConstraint("valor is null or valor >= 0", name="ck_nota_valor"))


class Aula(Base):
    __tablename__ = "aula"
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"))
    data: Mapped[str] = mapped_column(String(10))     # AAAA-MM-DD
    tema: Mapped[str] = mapped_column(String(120), default="")
    unidades: Mapped[int] = mapped_column(Integer, default=1)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    turma: Mapped[Turma] = relationship(back_populates="aulas")
    __table_args__ = (CheckConstraint("unidades > 0", name="ck_unidades"),)


class Presenca(Base):
    __tablename__ = "presenca"
    id: Mapped[int] = mapped_column(primary_key=True)
    matricula_id: Mapped[int] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"))
    aula_id: Mapped[int] = mapped_column(ForeignKey("aula.id", ondelete="CASCADE"))
    presente: Mapped[bool] = mapped_column(Boolean)
    versao: Mapped[int] = mapped_column(Integer, default=1)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    __table_args__ = (UniqueConstraint("matricula_id", "aula_id"),)


class Atividade(Base):
    """Atividade com prazo (lista, trabalho, entrega de projeto)."""
    __tablename__ = "atividade"
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turma.id", ondelete="CASCADE"))
    titulo: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(String(400), default="")
    prazo: Mapped[str] = mapped_column(String(10))     # AAAA-MM-DD
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    turma: Mapped[Turma] = relationship(back_populates="atividades")


class Entrega(Base):
    """Registro de que a matrícula entregou a atividade, e em que data."""
    __tablename__ = "entrega"
    id: Mapped[int] = mapped_column(primary_key=True)
    matricula_id: Mapped[int] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"))
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividade.id", ondelete="CASCADE"))
    entregue_em: Mapped[str] = mapped_column(String(10))   # AAAA-MM-DD
    __table_args__ = (UniqueConstraint("matricula_id", "atividade_id"),)


class HistoricoAlteracao(Base):
    """Rastro de cada correção: quem mudou, quando, de quanto para quanto."""
    __tablename__ = "historico_alteracao"
    id: Mapped[int] = mapped_column(primary_key=True)
    matricula_id: Mapped[int] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"))
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    tipo: Mapped[str] = mapped_column(String(20))       # nota | presenca | entrega
    referencia: Mapped[str] = mapped_column(String(120))
    valor_anterior: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    valor_novo: Mapped[str] = mapped_column(String(40))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    autor: Mapped[Usuario] = relationship()


class Analise(Base):
    __tablename__ = "analise"
    id: Mapped[int] = mapped_column(primary_key=True)
    matricula_id: Mapped[int] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"))
    solicitado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    criterio_id: Mapped[int] = mapped_column(ForeignKey("criterio.id"))
    versao_registros: Mapped[int] = mapped_column(Integer)
    versao_criterios: Mapped[str] = mapped_column(String(30))
    media: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    frequencia: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    presencas: Mapped[int] = mapped_column(Integer, default=0)
    unidades_consideradas: Mapped[int] = mapped_column(Integer, default=0)
    atividades_vencidas: Mapped[int] = mapped_column(Integer, default=0)
    atividades_sem_entrega: Mapped[int] = mapped_column(Integer, default=0)
    certeza: Mapped[float] = mapped_column(Float, default=0.0)
    prioridade: Mapped[str] = mapped_column(String(30))
    regras: Mapped[list] = mapped_column(JSON)          # ["R1","R2","R3"]
    acionadas: Mapped[list] = mapped_column(JSON)       # evidências de cada regra
    pendencias: Mapped[list] = mapped_column(JSON)
    fatos: Mapped[dict] = mapped_column(JSON)           # cópia fixa dos dados usados
    motivo: Mapped[str] = mapped_column(Text)
    sintese: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sintese_status: Mapped[str] = mapped_column(String(300), default="desativada")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    solicitado_por: Mapped[Usuario] = relationship()
    criterio: Mapped[Criterio] = relationship()
    revisoes: Mapped[list["Revisao"]] = relationship(
        back_populates="analise", order_by="Revisao.criado_em")


class Revisao(Base):
    __tablename__ = "revisao"
    id: Mapped[int] = mapped_column(primary_key=True)
    analise_id: Mapped[int] = mapped_column(ForeignKey("analise.id", ondelete="CASCADE"))
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    decisao: Mapped[str] = mapped_column(String(30))     # confirmado | ajustar_registro | sem_acao
    observacao: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    analise: Mapped[Analise] = relationship(back_populates="revisoes")
    autor: Mapped[Usuario] = relationship()


class PedidoConferencia(Base):
    __tablename__ = "pedido_conferencia"
    id: Mapped[int] = mapped_column(primary_key=True)
    matricula_id: Mapped[int] = mapped_column(ForeignKey("matricula.id", ondelete="CASCADE"))
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    # Registro a que o pedido se refere: avaliacao:<id>, aula:<id> ou geral
    referencia: Mapped[str] = mapped_column(String(40))
    referencia_rotulo: Mapped[str] = mapped_column(String(120))
    mensagem: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="aberto")   # aberto | respondido
    resposta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    respondido_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    autor: Mapped[Usuario] = relationship()
