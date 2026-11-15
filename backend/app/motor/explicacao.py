"""Monta o motivo em texto a partir do resultado do motor.

O texto é determinístico e só usa valores que o motor calculou. Ele mostra
dado e critério, sem tentar adivinhar a causa do desempenho do aluno.
"""

from __future__ import annotations

from typing import Optional

from .motor import Criterios, Resultado


def fmt_num(valor: Optional[float], casas: int = 1) -> str:
    if valor is None:
        return "—"
    return f"{valor:.{casas}f}".replace(".", ",")


def fmt_pct(valor: Optional[float]) -> str:
    if valor is None:
        return "—"
    if float(valor).is_integer():
        return f"{int(valor)}%"
    return f"{fmt_num(valor)}%"


def montar_motivo(r: Resultado, c: Criterios) -> str:
    partes: list[str] = []
    regras = {a.regra for a in r.acionadas}

    if "R1" in regras and "R2" in regras:
        partes.append(
            f"A média {fmt_num(r.media)} está abaixo do limite didático de "
            f"{fmt_num(c.media_minima)} e a frequência de {fmt_pct(r.frequencia)} "
            f"está abaixo de {fmt_pct(c.frequencia_minima)}. As regras R1 e R2 "
            f"sustentam a prioridade de conferência R3.")
    elif "R1" in regras:
        partes.append(
            f"A média {fmt_num(r.media)} está abaixo do limite didático de "
            f"{fmt_num(c.media_minima)} (R1).")
    elif "R2" in regras:
        partes.append(
            f"A frequência de {fmt_pct(r.frequencia)} está abaixo do limite de "
            f"{fmt_pct(c.frequencia_minima)} (R2).")

    for p in r.pendencias:
        nome = "A média" if p.indicador == "media" else "A frequência"
        partes.append(f"{nome} não pode ser avaliada: {p.motivo} (R4)")

    if not partes:
        partes.append(
            f"Média {fmt_num(r.media)} e frequência de {fmt_pct(r.frequencia)} "
            f"dentro dos critérios {c.versao}. Nenhuma regra de alerta foi acionada.")

    return " ".join(partes)
