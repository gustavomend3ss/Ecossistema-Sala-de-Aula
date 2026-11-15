"""Autenticação por token e verificação de vínculo (RF01 e RF02).

Toda rota protegida passa por aqui. A autorização é sempre conferida no
servidor; o aplicativo nunca decide sozinho o que o usuário pode ver.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import Matricula, Usuario, VinculoProfessorTurma

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


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def _assinar(carga: str) -> str:
    return _b64(hmac.new(config.SECRET_KEY.encode(), carga.encode(), hashlib.sha256).digest())


def criar_token(usuario: Usuario) -> tuple[str, datetime]:
    """Token assinado com HMAC-SHA256: id do usuário + validade.

    Não fica guardado no banco. Qualquer instância da API confere a assinatura
    sozinha, o que permite rodar em funções sem estado (Vercel).
    """
    expira = datetime.now(timezone.utc) + timedelta(hours=config.SESSAO_HORAS)
    carga = _b64(json.dumps({"uid": usuario.id, "exp": int(expira.timestamp()),
                             "n": secrets.token_hex(4)}).encode())
    return f"{carga}.{_assinar(carga)}", expira


def ler_token(token: str) -> int | None:
    """Devolve o id do usuário, ou None se o token for inválido ou vencido."""
    try:
        carga, assinatura = token.split(".")
        if not hmac.compare_digest(assinatura, _assinar(carga)):
            return None
        dados = json.loads(base64.urlsafe_b64decode(carga + "=" * (-len(carga) % 4)))
        if int(dados["exp"]) < time.time():
            return None
        return int(dados["uid"])
    except (ValueError, KeyError, TypeError):
        return None


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
    uid = ler_token(cred.credentials)
    usuario = db.get(Usuario, uid) if uid is not None else None
    if usuario is None:
        raise NAO_AUTENTICADO
    return usuario


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
