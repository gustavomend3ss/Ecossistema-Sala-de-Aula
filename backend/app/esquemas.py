"""Validação das entradas da API (o FastAPI rejeita o que não bate)."""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TextoEntrada(BaseModel):
    # Limpa antes das restrições de tamanho. Senhas não usam esta base.
    model_config = ConfigDict(str_strip_whitespace=True)


class LoginEntrada(BaseModel):
    login: str = Field(min_length=1, max_length=60)
    senha: str = Field(min_length=1, max_length=128)


class NotaEntrada(BaseModel):
    # A escala exata (0 a nota_maxima) é conferida no serviço, pela avaliação.
    valor: float = Field(ge=0, le=100)


class PresencaEntrada(BaseModel):
    presente: bool


class RevisaoEntrada(TextoEntrada):
    decisao: Literal["confirmado", "ajustar_registro", "sem_acao"]
    observacao: str = Field(min_length=3, max_length=1000)


class ConferenciaEntrada(TextoEntrada):
    referencia: str = Field(pattern=r"^(avaliacao:\d+|aula:\d+|atividade:\d+|geral)$")
    mensagem: str = Field(min_length=5, max_length=1000)


class RespostaEntrada(TextoEntrada):
    resposta: str = Field(min_length=2, max_length=1000)


class PerguntaEntrada(TextoEntrada):
    pergunta: str = Field(min_length=2, max_length=500)


class MensagemEntrada(TextoEntrada):
    """Pergunta ao assistente. Sem conversa_id, começa uma conversa nova."""
    pergunta: str = Field(min_length=2, max_length=500)
    conversa_id: Optional[int] = Field(default=None, ge=1)


class AtividadeEntrada(BaseModel):
    titulo: str = Field(min_length=3, max_length=120)
    prazo: date
    descricao: str = Field(default="", max_length=400)

    @field_validator("titulo", "descricao")
    @classmethod
    def _limpar(cls, v: str) -> str:
        # Sanitização: espaços extras e caracteres de controle saem antes de salvar
        return " ".join("".join(c if c.isprintable() else " " for c in v).split())


class EntregaEntrada(BaseModel):
    entregue: bool
