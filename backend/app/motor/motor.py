"""Motor de regras do assistente docente.

Agente baseado em conhecimento (Russell; Norvig, 2022) com inferência por
encadeamento para a frente sobre cláusulas definidas (Poole; Mackworth, 2023).
Cada regra carrega um fator de certeza, no modelo do MYCIN (Shortliffe;
Buchanan, 1975), usado para graduar a necessidade de acompanhamento.

O motor é puro: recebe fatos e critérios, devolve um resultado. Não acessa
banco, rede nem relógio. Por isso a mesma entrada sempre produz a mesma saída,
e ele pode ser testado isolado do resto do sistema.
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


# Situação de uma atividade para a matrícula, calculada pelo serviço na data
# da análise: entregue | entregue_atraso | atrasada (venceu sem entrega) | aberta
SITUACOES_ENTREGA = ("entregue", "entregue_atraso", "atrasada", "aberta")


@dataclass(frozen=True)
class EntregaFato:
    atividade: str
    prazo: str
    situacao: str


@dataclass(frozen=True)
class Fatos:
    matricula: str
    notas: tuple[NotaFato, ...]
    presencas: tuple[PresencaFato, ...]
    versao_registros: int = 1
    entregas: tuple[EntregaFato, ...] = ()


@dataclass(frozen=True)
class Criterios:
    versao: str
    media_minima: float
    frequencia_minima: float
    # Quantas atividades vencidas sem entrega são toleradas antes de R6.
    atrasos_maximos: int = 1


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------

@dataclass
class RegraAcionada:
    regra: str
    corpo: list[str]
    cabeca: str
    evidencia: dict
    fc: float = 1.0

    def como_dict(self) -> dict:
        return {"regra": self.regra, "corpo": self.corpo, "cabeca": self.cabeca,
                "evidencia": self.evidencia, "fc": self.fc}


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
    atividades_vencidas: int = 0
    entregas_no_prazo: int = 0
    entregas_atrasadas: int = 0      # entregues depois do prazo
    atividades_sem_entrega: int = 0  # venceram e não foram entregues
    pendencias: list[Pendencia] = field(default_factory=list)
    acionadas: list[RegraAcionada] = field(default_factory=list)
    base: set[str] = field(default_factory=set)
    fc_fatos: dict[str, float] = field(default_factory=dict)
    certeza: float = 0.0

    # -- registro ---------------------------------------------------------
    def nao_avaliavel(self, indicador: str, motivo: str) -> None:
        self.pendencias.append(Pendencia(indicador, "R4", motivo))

    def registrar(self, regra: str, corpo: set[str], cabeca: str,
                  evidencia: dict, fc: float) -> None:
        self.acionadas.append(
            RegraAcionada(regra, sorted(corpo), cabeca, evidencia, fc))

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
        for fato in ("prioridade_alta", "alerta_media", "alerta_frequencia", "alerta_entregas"):
            if fato in self.base:
                return fato
        if self.pendencias:
            return "conferir_dados"
        return "sem_alerta"

    @property
    def taxa_entrega(self) -> Optional[float]:
        if self.atividades_vencidas == 0:
            return None
        entregues = self.entregas_no_prazo + self.entregas_atrasadas
        return _arredonda(entregues * 100 / self.atividades_vencidas)


# ---------------------------------------------------------------------------
# Cálculo dos indicadores (fórmulas 1 e 2 do documento do Bloco 2)
# ---------------------------------------------------------------------------

def _arredonda(valor: float) -> float:
    # Duas casas antes de comparar evita artefatos de ponto flutuante,
    # como 5,9999999 sendo tratado como menor que 6,0.
    return round(valor + 0.0, 2)


def calcular_media(fatos: Fatos, resultado: Resultado) -> Optional[float]:
    """média = Σ(notaᵢ × pesoᵢ) ÷ Σ pesoᵢ, ou None se faltar dado (R4)."""
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
    """frequência = presenças ÷ unidades-aula consideradas × 100, ou None (R4)."""
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


def contar_entregas(fatos: Fatos, resultado: Resultado) -> None:
    """Conta só atividades vencidas. Atividade ainda aberta não pesa contra."""
    for e in fatos.entregas:
        if e.situacao == "entregue":
            resultado.entregas_no_prazo += 1
        elif e.situacao == "entregue_atraso":
            resultado.entregas_atrasadas += 1
        elif e.situacao == "atrasada":
            resultado.atividades_sem_entrega += 1
    resultado.atividades_vencidas = (resultado.entregas_no_prazo
                                     + resultado.entregas_atrasadas
                                     + resultado.atividades_sem_entrega)


# ---------------------------------------------------------------------------
# Base de regras, fatores de certeza e inferência
# ---------------------------------------------------------------------------

# Cláusulas definidas: (nome, corpo, cabeça, fator de certeza da regra).
# R4 e R5 não entram aqui: R4 é verificada antes (completude) e R5 trata do
# histórico, fora do motor. Os fatores foram definidos pelo grupo como grau de
# confiança de que a conclusão indica necessidade de acompanhamento; são
# heurísticos, como no MYCIN, e ficam na base de conhecimento, não no código
# de inferência.
REGRAS: tuple[tuple[str, frozenset[str], str, float], ...] = (
    ("R1", frozenset({"media_baixa"}), "alerta_media", 0.7),
    ("R2", frozenset({"frequencia_baixa"}), "alerta_frequencia", 0.6),
    ("R3", frozenset({"alerta_media", "alerta_frequencia"}), "prioridade_alta", 0.9),
    ("R6", frozenset({"entregas_vencidas"}), "alerta_entregas", 0.5),
)

# Conclusões que contam como evidência independente de necessidade de
# acompanhamento. R3 não entra na soma: ela reorganiza a prioridade, mas é
# derivada de R1 e R2, e somá-la contaria a mesma evidência duas vezes.
EVIDENCIAS_DE_ACOMPANHAMENTO = ("alerta_media", "alerta_frequencia", "alerta_entregas")

# Volume mínimo de dados para o fato ter certeza total. Abaixo disso, o fato
# vale proporcionalmente menos (poucas aulas dizem pouco sobre frequência).
UNIDADES_REFERENCIA = 10
ATIVIDADES_REFERENCIA = 3

DESCRICAO_REGRAS = {
    "R1": "Média avaliável menor que o mínimo → alerta de média",
    "R2": "Frequência avaliável menor que o mínimo → alerta de frequência",
    "R3": "R1 e R2 ao mesmo tempo → prioridade alta de conferência",
    "R4": "Dado ausente ou inconsistente → indicador não avaliável, com pendência",
    "R5": "Registro ou critério atualizado → nova análise, anterior mantida no histórico",
    "R6": "Atividades vencidas sem entrega acima do limite → alerta de entregas",
}


def combinar_fc(fc1: float, fc2: float) -> float:
    """Combinação paralela de duas evidências positivas (MYCIN)."""
    return fc1 + fc2 * (1 - fc1)


def analisar(fatos: Fatos, criterios: Criterios) -> Resultado:
    resultado = Resultado(versao_criterios=criterios.versao)

    # Completude (R4) e cálculo
    media = calcular_media(fatos, resultado)
    freq = calcular_frequencia(fatos, resultado)
    contar_entregas(fatos, resultado)
    resultado.media = media
    resultado.frequencia = freq

    # Comparações numéricas viram fatos proposicionais, cada um com a
    # certeza que o volume de dados permite.
    base: set[str] = set()
    fc: dict[str, float] = {}
    evidencias: dict[str, dict] = {}
    if media is not None and media < criterios.media_minima:
        base.add("media_baixa")
        fc["media_baixa"] = 1.0
        evidencias["media_baixa"] = {
            "indicador": "media", "valor": media,
            "limite": criterios.media_minima, "comparacao": "<"}
    if freq is not None and freq < criterios.frequencia_minima:
        base.add("frequencia_baixa")
        fc["frequencia_baixa"] = round(
            min(1.0, resultado.unidades_consideradas / UNIDADES_REFERENCIA), 2)
        evidencias["frequencia_baixa"] = {
            "indicador": "frequencia", "valor": freq,
            "limite": criterios.frequencia_minima, "comparacao": "<"}
    if resultado.atividades_sem_entrega > criterios.atrasos_maximos:
        base.add("entregas_vencidas")
        fc["entregas_vencidas"] = round(
            min(1.0, resultado.atividades_vencidas / ATIVIDADES_REFERENCIA), 2)
        evidencias["entregas_vencidas"] = {
            "indicador": "entregas", "valor": resultado.atividades_sem_entrega,
            "limite": criterios.atrasos_maximos, "comparacao": ">"}

    # Encadeamento para a frente até o ponto fixo.
    # FC da conclusão = mínimo dos FC do corpo (conjunção) × FC da regra.
    mudou = True
    while mudou:
        mudou = False
        for nome, corpo, cabeca, fc_regra in REGRAS:
            if corpo <= base and cabeca not in base:
                base.add(cabeca)
                fc[cabeca] = round(min(fc[c] for c in corpo) * fc_regra, 4)
                evid = {k: evidencias[k] for k in corpo if k in evidencias}
                if not evid:   # R3: a evidência são as regras anteriores
                    evid = {"derivado_de": sorted(corpo)}
                resultado.registrar(nome, set(corpo), cabeca, evid, fc[cabeca])
                mudou = True

    # Grau de certeza da necessidade de acompanhamento: combinação paralela
    # das evidências independentes que foram concluídas.
    certeza = 0.0
    for fato in EVIDENCIAS_DE_ACOMPANHAMENTO:
        if fato in fc:
            certeza = combinar_fc(certeza, fc[fato])

    resultado.base = base
    resultado.fc_fatos = fc
    resultado.certeza = round(certeza, 2)
    return resultado
