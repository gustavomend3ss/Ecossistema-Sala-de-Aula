"""Motor de regras do assistente docente.

Agente baseado em conhecimento (Russell; Norvig, 2022) com inferência por
encadeamento para a frente sobre cláusulas definidas (Poole; Mackworth, 2023).

O motor é puro: recebe fatos e critérios, devolve um resultado. Não acessa
banco, rede nem relógio. Por isso a mesma entrada sempre produz a mesma saída,
e ele pode ser testado isolado do resto do sistema (casos T01 a T05).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NotaFato:
    avaliacao: str
    peso: float
    obrigatoria: bool
    valor: Optional[float]          # None = nota não lançada (nunca vira zero)
    nota_maxima: float = 10.0


@dataclass(frozen=True)
class PresencaFato:
    aula: str
    unidades: int
    presente: Optional[bool]        # None = presença não registrada


@dataclass(frozen=True)
class Fatos:
    matricula: str
    notas: tuple[NotaFato, ...]
    presencas: tuple[PresencaFato, ...]
    versao_registros: int = 1


@dataclass(frozen=True)
class Criterios:
    versao: str
    media_minima: float
    frequencia_minima: float


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------

@dataclass
class RegraAcionada:
    regra: str
    corpo: list[str]
    cabeca: str
    evidencia: dict

    def como_dict(self) -> dict:
        return {"regra": self.regra, "corpo": self.corpo,
                "cabeca": self.cabeca, "evidencia": self.evidencia}


@dataclass
class Pendencia:
    indicador: str
    regra: str
    motivo: str

    def como_dict(self) -> dict:
        return {"indicador": self.indicador, "regra": self.regra,
                "motivo": self.motivo}


@dataclass
class Resultado:
    versao_criterios: str
    media: Optional[float] = None
    frequencia: Optional[float] = None
    presencas: int = 0
    unidades_consideradas: int = 0
    pendencias: list[Pendencia] = field(default_factory=list)
    acionadas: list[RegraAcionada] = field(default_factory=list)
    base: set[str] = field(default_factory=set)

    # -- registro ---------------------------------------------------------
    def nao_avaliavel(self, indicador: str, motivo: str) -> None:
        self.pendencias.append(Pendencia(indicador, "R4", motivo))

    def registrar(self, regra: str, corpo: set[str], cabeca: str,
                  evidencia: dict) -> None:
        self.acionadas.append(
            RegraAcionada(regra, sorted(corpo), cabeca, evidencia))

    # -- leitura ----------------------------------------------------------
    @property
    def regras(self) -> list[str]:
        regras = [a.regra for a in self.acionadas]
        if self.pendencias:
            regras.append("R4")
        return regras

    @property
    def prioridade(self) -> str:
        """Resumo para a coluna 'Acompanhamento' da tela da turma."""
        if "prioridade_alta" in self.base:
            return "prioridade_alta"
        if "alerta_media" in self.base:
            return "alerta_media"
        if "alerta_frequencia" in self.base:
            return "alerta_frequencia"
        if self.pendencias:
            return "conferir_dados"
        return "sem_alerta"

    @property
    def completude(self) -> dict:
        avaliaveis = {p.indicador for p in self.pendencias}
        return {
            "media": "media" not in avaliaveis,
            "frequencia": "frequencia" not in avaliaveis,
        }


# ---------------------------------------------------------------------------
# Cálculo dos indicadores (fórmulas 1 e 2 do documento do Bloco 2)
# ---------------------------------------------------------------------------

def _arredonda(valor: float) -> float:
    # Duas casas antes de comparar evita artefatos de ponto flutuante,
    # como 5,9999999 sendo tratado como menor que 6,0.
    return round(valor + 0.0, 2)


def calcular_media(fatos: Fatos, resultado: Resultado) -> Optional[float]:
    """média = Σ(notaᵢ × pesoᵢ) ÷ Σ pesoᵢ — ou None se faltar dado (R4)."""
    if not fatos.notas:
        resultado.nao_avaliavel("media", "Nenhuma avaliação cadastrada.")
        return None

    problemas: list[str] = []
    soma = 0.0
    pesos = 0.0
    for n in fatos.notas:
        if n.valor is None:
            if n.obrigatoria:
                problemas.append(f"{n.avaliacao} sem nota lançada")
            continue
        if not (0 <= n.valor <= n.nota_maxima):
            problemas.append(
                f"{n.avaliacao} com nota {n.valor} fora da escala 0 a {n.nota_maxima:g}")
            continue
        if n.peso <= 0:
            problemas.append(f"{n.avaliacao} com peso inválido ({n.peso})")
            continue
        soma += n.valor * n.peso
        pesos += n.peso

    if problemas:
        resultado.nao_avaliavel("media", "; ".join(problemas) + ".")
        return None
    if pesos == 0:
        resultado.nao_avaliavel("media", "Nenhuma nota lançada.")
        return None
    return _arredonda(soma / pesos)


def calcular_frequencia(fatos: Fatos, resultado: Resultado) -> Optional[float]:
    """frequência = presenças ÷ unidades-aula consideradas × 100 — ou None (R4)."""
    if not fatos.presencas:
        resultado.nao_avaliavel("frequencia", "Nenhuma aula registrada.")
        return None

    sem_registro = [p.aula for p in fatos.presencas if p.presente is None]
    if sem_registro:
        lista = ", ".join(sem_registro[:3])
        extra = f" e mais {len(sem_registro) - 3}" if len(sem_registro) > 3 else ""
        resultado.nao_avaliavel(
            "frequencia", f"Presença não registrada em: {lista}{extra}.")
        return None

    invalidas = [p.aula for p in fatos.presencas if p.unidades <= 0]
    if invalidas:
        resultado.nao_avaliavel(
            "frequencia", f"Aula com unidades inválidas: {', '.join(invalidas)}.")
        return None

    total = sum(p.unidades for p in fatos.presencas)
    presentes = sum(p.unidades for p in fatos.presencas if p.presente)
    resultado.presencas = presentes
    resultado.unidades_consideradas = total
    # multiplicar antes de dividir mantém 20/25 exatamente em 80,0
    return _arredonda(presentes * 100 / total)


# ---------------------------------------------------------------------------
# Base de regras e inferência
# ---------------------------------------------------------------------------

# Cláusulas definidas: (nome, corpo, cabeça). R4 e R5 não entram aqui:
# R4 é verificada antes (completude) e R5 trata do histórico, fora do motor.
REGRAS: tuple[tuple[str, frozenset[str], str], ...] = (
    ("R1", frozenset({"media_baixa"}), "alerta_media"),
    ("R2", frozenset({"frequencia_baixa"}), "alerta_frequencia"),
    ("R3", frozenset({"alerta_media", "alerta_frequencia"}), "prioridade_alta"),
)

DESCRICAO_REGRAS = {
    "R1": "Média avaliável menor que o mínimo → alerta de média",
    "R2": "Frequência avaliável menor que o mínimo → alerta de frequência",
    "R3": "R1 e R2 ao mesmo tempo → prioridade alta de conferência",
    "R4": "Dado ausente ou inconsistente → indicador não avaliável, com pendência",
    "R5": "Registro ou critério atualizado → nova análise, anterior mantida no histórico",
}


def analisar(fatos: Fatos, criterios: Criterios) -> Resultado:
    resultado = Resultado(versao_criterios=criterios.versao)

    # Passo 2 e 3: completude (R4) e cálculo
    media = calcular_media(fatos, resultado)
    freq = calcular_frequencia(fatos, resultado)
    resultado.media = media
    resultado.frequencia = freq

    # Comparações numéricas viram fatos proposicionais
    base: set[str] = set()
    evidencias: dict[str, dict] = {}
    if media is not None and media < criterios.media_minima:
        base.add("media_baixa")
        evidencias["media_baixa"] = {
            "indicador": "media", "valor": media,
            "limite": criterios.media_minima, "comparacao": "<"}
    if freq is not None and freq < criterios.frequencia_minima:
        base.add("frequencia_baixa")
        evidencias["frequencia_baixa"] = {
            "indicador": "frequencia", "valor": freq,
            "limite": criterios.frequencia_minima, "comparacao": "<"}

    # Passo 4: encadeamento para a frente até o ponto fixo
    mudou = True
    while mudou:
        mudou = False
        for nome, corpo, cabeca in REGRAS:
            if corpo <= base and cabeca not in base:
                base.add(cabeca)
                evid = {k: evidencias[k] for k in corpo if k in evidencias}
                if not evid:   # R3: a evidência são as regras anteriores
                    evid = {"derivado_de": sorted(corpo)}
                resultado.registrar(nome, set(corpo), cabeca, evid)
                mudou = True

    resultado.base = base
    return resultado
