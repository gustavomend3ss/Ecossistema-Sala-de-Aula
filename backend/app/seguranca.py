"""Autenticação por token e verificação de vínculo (RF01 e RF02).

Toda rota protegida passa por aqui. A autorização é sempre conferida no
servidor; o aplicativo nunca decide sozinho o que o usuário pode ver.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import Matricula, Sessao, Usuario, VinculoProfessorTurma

_ITERACOES = 200_000


def gerar_hash(senha: str) -> str:
    sal = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), _ITERACOES)
    return f"pbkdf2_sha256${_ITERACOES}${sal}${dk.hex()}"


def conferir_senha(senha: str, armazenado: str) -> bool:
    try:
        _, iteracoes, sal, esperado = armazenado.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), int(iteracoes))
        return hmac.compare_digest(dk.hex(), esperado)
    except (ValueError, TypeError):
        return False


def criar_sessao(db: Session, usuario: Usuario) -> Sessao:
    sessao = Sessao(
        token=secrets.token_urlsafe(32),
        usuario_id=usuario.id,
        expira_em=datetime.now(timezone.utc) + timedelta(hours=config.SESSAO_HORAS),
    )
    db.add(sessao)
    db.commit()
    return sessao


_bearer = HTTPBearer(auto_error=False)

NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sessão ausente ou expirada. Entre novamente.",
    headers={"WWW-Authenticate": "Bearer"},
)
# Mesma resposta para "não existe" e "não é seu": não confirma a existência
# de turma ou matrícula de outra pessoa (caso T06).
ACESSO_NEGADO = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Registro não encontrado ou sem permissão de acesso.",
)


def usuario_atual(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if cred is None:
        raise NAO_AUTENTICADO
    sessao = db.get(Sessao, cred.credentials)
    if sessao is None:
        raise NAO_AUTENTICADO
    expira = sessao.expira_em
    if expira.tzinfo is None:   # SQLite devolve datetime sem fuso
        expira = expira.replace(tzinfo=timezone.utc)
    if expira < datetime.now(timezone.utc):
        db.delete(sessao)
        db.commit()
        raise NAO_AUTENTICADO
    return sessao.usuario


def exigir_professor(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    if usuario.perfil != "professor":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Ação disponível apenas para o perfil professor.")
    return usuario


def professor_tem_turma(db: Session, professor_id: int, turma_id: int) -> bool:
    return db.scalar(
        select(VinculoProfessorTurma.id).where(
            VinculoProfessorTurma.professor_id == professor_id,
            VinculoProfessorTurma.turma_id == turma_id)) is not None


def exigir_turma(db: Session, usuario: Usuario, turma_id: int) -> None:
    if usuario.perfil != "professor" or not professor_tem_turma(db, usuario.id, turma_id):
        raise ACESSO_NEGADO


def obter_matricula(db: Session, usuario: Usuario, matricula_id: int) -> Matricula:
    """Devolve a matrícula só se o usuário tiver vínculo com ela."""
    m = db.get(Matricula, matricula_id)
    if m is None:
        raise ACESSO_NEGADO
    if usuario.perfil == "aluno" and m.aluno_id == usuario.id:
        return m
    if usuario.perfil == "professor" and professor_tem_turma(db, usuario.id, m.turma_id):
        return m
    raise ACESSO_NEGADO
