"""Validação das entradas da API (o FastAPI rejeita o que não bate)."""

from typing import Literal

from pydantic import BaseModel, Field


class LoginEntrada(BaseModel):
    login: str = Field(min_length=1, max_length=60)
    senha: str = Field(min_length=1, max_length=128)


class NotaEntrada(BaseModel):
    # A escala exata (0 a nota_maxima) é conferida no serviço, pela avaliação.
    valor: float = Field(ge=0, le=100)


class PresencaEntrada(BaseModel):
    presente: bool


class RevisaoEntrada(BaseModel):
    decisao: Literal["confirmado", "ajustar_registro", "sem_acao"]
    observacao: str = Field(min_length=3, max_length=1000)


class ConferenciaEntrada(BaseModel):
    referencia: str = Field(pattern=r"^(avaliacao:\d+|aula:\d+|geral)$")
    mensagem: str = Field(min_length=5, max_length=1000)


class RespostaEntrada(BaseModel):
    resposta: str = Field(min_length=2, max_length=1000)


class PerguntaEntrada(BaseModel):
    pergunta: str = Field(min_length=2, max_length=500)
