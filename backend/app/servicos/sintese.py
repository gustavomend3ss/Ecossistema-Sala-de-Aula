"""Adaptador opcional do Gemini para a síntese em texto.

Regras do documento do Bloco 2:
- o modelo recebe apenas fatos que o motor já calculou;
- a resposta vem em formato estruturado (JSON);
- antes de exibir, a API confere números, regras e pendências;
- se a síntese inventar causa, mudar valor, esquecer pendência ou falhar,
  ela é descartada e a tela mostra o relatório estruturado (caso T09).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Optional

from pydantic import BaseModel

from .. import config
from ..motor import fmt_num, fmt_pct

# Função que recebe o prompt e devolve o texto JSON do modelo. Nos testes,
# é trocada por uma falsa; em produção, chama a API REST do Gemini.
Chamador = Callable[[str], str]

TERMOS_CAUSAIS = (
    "porque", "devido", "por causa", "em razão", "desmotiv", "desinteress",
    "preguiç", "família", "familia", "pessoal", "saúde", "saude", "emocional",
    "provavelmente", "talvez", "deve estar", "parece que",
)

class SinteseModelo(BaseModel):
    """Formato estruturado que o Gemini deve devolver."""
    texto: str
    regras_citadas: list[str]


@dataclass
class Sintese:
    status: str                 # desativada | aprovada | descartada | indisponivel
    texto: Optional[str] = None
    motivo: str = ""


def montar_prompt(fatos_motor: dict) -> str:
    return (
        "Você apoia um professor universitário. Reescreva o relatório abaixo em no máximo "
        "três frases simples, em português do Brasil. Use SOMENTE os números e regras do "
        "relatório. Cite cada regra pelo código (R1, R2, R3, R4, R6). Se houver pendência, diga "
        "que o indicador não pode ser avaliado. NÃO sugira causas para o desempenho do aluno, "
        "NÃO dê conselhos e NÃO decida aprovação.\n\n"
        f"RELATÓRIO (JSON):\n{json.dumps(fatos_motor, ensure_ascii=False)}"
    )


def _chamar_gemini(prompt: str) -> str:
    """Chama o Gemini pelo SDK oficial (google-genai), pedindo JSON no esquema
    SinteseModelo. O import fica aqui dentro para a API subir mesmo sem o
    pacote instalado quando a síntese está desativada."""
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=config.GEMINI_API_KEY)
    resposta = cliente.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=SinteseModelo,
            http_options=types.HttpOptions(timeout=int(config.GEMINI_TIMEOUT * 1000)),
        ),
    )
    return resposta.text or ""


def _numeros_permitidos(f: dict) -> set[str]:
    valores: list[float] = []
    for chave in ("media", "frequencia", "media_minima", "frequencia_minima",
                  "presencas", "unidades_consideradas", "atividades_vencidas",
                  "atividades_sem_entrega", "atrasos_maximos", "grau_de_certeza"):
        v = f.get(chave)
        if v is not None:
            valores.append(float(v))
    permitidos: set[str] = set()
    for v in valores:
        permitidos.update({fmt_num(v), fmt_num(v, 2), fmt_pct(v).rstrip("%"),
                           str(v), f"{v:g}"})
        if v.is_integer():
            permitidos.add(str(int(v)))
    return permitidos


def verificar(texto: str, regras_citadas: list[str], f: dict) -> tuple[bool, str]:
    """Confere a síntese contra o resultado do motor. Devolve (ok, motivo)."""
    if not texto or not texto.strip():
        return False, "síntese vazia"

    baixo = texto.lower()
    for termo in TERMOS_CAUSAIS:
        if termo in baixo:
            return False, f"síntese sugere causa ou suposição ('{termo}')"

    esperadas = set(f["regras"])
    no_texto = set(re.findall(r"\bR[1-6]\b", texto))
    citadas = no_texto | {r.strip().upper() for r in regras_citadas}
    if citadas - esperadas:
        return False, f"síntese cita regra não acionada: {sorted(citadas - esperadas)}"
    if esperadas - no_texto:
        return False, f"síntese omite regra acionada: {sorted(esperadas - no_texto)}"

    if f["pendencias"] and not re.search(r"pend|não (pode ser |é )?avali", baixo):
        return False, "síntese omite a pendência"

    limpo = re.sub(r"\bR[1-6]\b", " ", texto)
    limpo = limpo.replace(f["versao_criterios"], " ")
    permitidos = _numeros_permitidos(f)
    for num in re.findall(r"\d+(?:[.,]\d+)?", limpo):
        if num not in permitidos and num.replace(".", ",") not in permitidos:
            return False, f"síntese cita número que não está no resultado: {num}"
    return True, ""


def gerar_sintese(fatos_motor: dict, chamar: Optional[Chamador] = None) -> Sintese:
    if chamar is None:
        if not config.GEMINI_API_KEY:
            return Sintese("desativada")
        chamar = _chamar_gemini
    try:
        bruto = chamar(montar_prompt(fatos_motor))
        dados = json.loads(bruto)
        texto = str(dados.get("texto", "")).strip()
        regras = [str(r) for r in dados.get("regras_citadas", [])]
    except Exception as erro:   # rede, cota, JSON inválido...
        return Sintese("indisponivel", motivo=type(erro).__name__)
    ok, motivo = verificar(texto, regras, fatos_motor)
    if not ok:
        return Sintese("descartada", motivo=motivo)
    return Sintese("aprovada", texto=texto)


# Ponto de troca para testes (T09). None = comportamento normal.
chamador_padrao: Optional[Chamador] = None
