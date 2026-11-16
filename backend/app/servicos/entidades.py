"""Reconhecimento de disciplinas, estudantes e professores citados numa
pergunta, com correspondência aproximada (RapidFuzz).

A comparação nunca é feita com a pergunta inteira. Primeiro a pergunta vira
uma lista de trechos candidatos (janelas de palavras sem conectivos nas
pontas); só esses trechos são comparados com os nomes reais vindos do banco,
e só com os registros que o usuário pode ver.

- Nome completo, com ou sem erro de digitação: token_sort_ratio entre a
  janela e o nome ("estrututa de dados" e "Estrutura de Dados" dão 94).
- Nome incompleto ("desenvolvimento web", "gráfica"): token_set_ratio,
  com desconto pela parte do nome que faltou. Palavras genéricas como
  "dados" ou "sistemas" não identificam uma disciplina sozinhas.
- Siglas: as iniciais das palavras do nome (IA, ED, CG).
- Pessoas: primeiro nome sozinho ou nome e sobrenome. Sobrenome sozinho não
  conta, para "dias" em "quantos dias" não virar a Carla Dias.

O resultado diz se o nome foi reconhecido, se precisa de confirmação, se é
ambíguo ou se não foi encontrado. Os limiares ficam em config.py.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Optional

from rapidfuzz import fuzz

from .. import config

PARADAS = {
    "a", "o", "as", "os", "e", "de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos",
    "um", "uma", "para", "pra", "com", "que", "qual", "quais", "quem", "como", "onde", "quando",
    "minha", "meu", "minhas", "meus", "sua", "seu", "me", "mostre", "mostra", "liste", "listar",
    "turma", "turmas", "disciplina", "disciplinas", "materia", "aluno", "alunos", "aluna", "alunas",
    "estudante", "estudantes", "professor", "professora", "prof", "esta", "estao", "sao", "tem",
    "ha", "ter", "sobre", "nota", "notas", "media", "medias", "falta", "faltas", "frequencia",
    "presenca", "entrega", "entregas", "atividade", "atividades", "risco", "reprovar", "correndo",
    "baixo", "baixa", "desempenho", "muitas", "muito", "tambem", "deles", "delas", "eles", "elas",
    "esses", "essas", "desses", "dessas", "isso", "ele", "ela", "dele", "dela", "precisa",
    "precisam", "acompanhamento", "alerta", "alertas", "pendente", "pendentes", "por", "porque",
    "explique", "explica", "sugira", "sugestao", "intervencao", "resumo", "geral", "agora",
    "ainda", "so", "ja", "mais", "menos", "mesmo", "todos", "todas", "cada", "voce", "pode",
    "poderia", "quero", "ver", "saber", "situacao", "andamento", "atrasado", "atrasados", "lancada",
    "lancadas", "lancamento", "sem", "nao", "sim", "ok", "obrigado", "obrigada", "oi", "ola",
    "semestre", "bimestre", "periodo", "ano", "mes", "semana", "hoje", "ontem", "momento", "sala",
    "aula", "aulas", "classe", "curso", "geral", "total", "atual", "ultima", "ultimo", "prova",
    "provas", "avaliacao", "avaliacoes", "trabalho", "trabalhos", "prazo", "prazos", "lista",
    "listas", "chamada", "grupo", "nesse", "nessa", "neste", "nesta", "tempo", "dia", "dias",
    "final", "finais", "parcial", "parciais", "recuperacao", "exame", "exames", "projeto",
    "projetos", "unidade", "unidades", "conteudo", "conteudos", "materia", "materias", "estudo",
}
# Palavras que aparecem em nomes de disciplinas mas são comuns demais para
# identificar uma delas sozinhas.
GENERICAS = {"dados", "sistema", "sistemas", "computacao", "introducao", "fundamentos",
             "engenharia", "projeto", "projetos", "i", "ii", "iii"}


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e sem pontuação, com espaços simples."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t.lower())).strip()


def palavras(texto: str) -> list[str]:
    return normalizar(texto).split()


def janelas(texto: str, maximo: int = 5) -> list[str]:
    """Trechos de 1 a `maximo` palavras que não começam nem terminam com
    conectivo. São os únicos pedaços da pergunta comparados com os nomes."""
    tk = palavras(texto)
    saida: list[str] = []
    for i in range(len(tk)):
        for j in range(i + 1, min(len(tk), i + maximo) + 1):
            w = tk[i:j]
            if w[0] in PARADAS or w[-1] in PARADAS:
                continue
            saida.append(" ".join(w))
    return saida


def sigla(nome: str) -> str:
    return "".join(p[0] for p in palavras(nome) if p not in PARADAS)


@dataclass
class Opcao:
    id: int
    nome: str
    pontos: float
    detalhe: str = ""

    def como_dict(self) -> dict:
        return {"id": self.id, "nome": self.nome, "pontos": round(self.pontos, 1),
                "detalhe": self.detalhe}


@dataclass
class Resolucao:
    tipo: str                      # disciplina | aluno | professor
    termo: str                     # trecho da pergunta que gerou a busca
    status: str                    # unico | confirmar | ambiguo | nenhum
    escolhido: Optional[Opcao] = None
    opcoes: list[Opcao] = field(default_factory=list)


def _decidir(tipo: str, pontuados: list[tuple[Opcao, str]], termo_explicito: str = "") -> Optional[Resolucao]:
    """Aplica os limiares: aceite direto, confirmação, ambiguidade ou nada."""
    if not pontuados:
        if termo_explicito:
            return Resolucao(tipo, termo_explicito, "nenhum")
        return None
    pontuados.sort(key=lambda p: -p[0].pontos)
    melhor, termo = pontuados[0]
    if melhor.pontos < config.FUZZY_SUGESTAO:
        if termo_explicito:
            return Resolucao(tipo, termo_explicito, "nenhum",
                             opcoes=[o for o, _ in pontuados[:3]])
        return None
    proximos = [o for o, _ in pontuados if melhor.pontos - o.pontos <= config.FUZZY_MARGEM]
    if len(proximos) > 1:
        return Resolucao(tipo, termo, "ambiguo", opcoes=proximos)
    if melhor.pontos >= config.FUZZY_ACEITE:
        return Resolucao(tipo, termo, "unico", escolhido=melhor, opcoes=[melhor])
    return Resolucao(tipo, termo, "confirmar", escolhido=melhor, opcoes=[melhor])


_MENCAO_DISCIPLINA = re.compile(
    r"\b(?:turma|disciplina|materia|cadeira)\s+(?:de|da|do|em)\s+([a-z0-9 ]{3,60})")


def _termo_explicito(pergunta: str) -> str:
    """Trecho depois de 'turma de', 'disciplina de'...: se nada casar com ele,
    a resposta deve dizer que a disciplina não foi encontrada."""
    m = _MENCAO_DISCIPLINA.search(normalizar(pergunta))
    if not m:
        return ""
    termo: list[str] = []
    for p in m.group(1).split():
        if p in PARADAS and termo:
            break
        if p not in PARADAS:
            termo.append(p)
        if len(termo) == 4:
            break
    return " ".join(termo)


_FIM_DE_FRASE = re.compile(r"\b(?:em|de|da|do|na|no)\s+((?:[a-z0-9]+\s?){1,4})$")


def termo_no_fim(pergunta: str) -> str:
    """Trecho que fecha a pergunta depois de 'em', 'de', 'na'... ("frequência em
    física quântica"). Serve para avisar que a disciplina não existe quando
    nada casou. Palavras comuns não contam."""
    m = _FIM_DE_FRASE.search(normalizar(pergunta))
    if not m:
        return ""
    sig = [p for p in m.group(1).split() if p not in PARADAS]
    if not sig or (len(sig) == 1 and len(sig[0]) < 6) or not any(len(p) >= 5 for p in sig):
        return ""
    return " ".join(sig)


def pontuar_disciplina(trecho: str, nome: str) -> float:
    """Pontuação de 0 a 100 entre um trecho da pergunta e um nome de disciplina."""
    n = normalizar(nome)
    sig_n = [p for p in n.split() if p not in PARADAS]
    sig_t = [p for p in trecho.split() if p not in PARADAS]
    if not sig_t:
        return 0.0
    if len(sig_t) == 1 and len(sig_t[0]) <= 4 and sig_t[0] == sigla(nome) and len(sig_n) > 1:
        return 97.0                                    # sigla: IA, ED, CG
    completo = float(fuzz.token_sort_ratio(trecho, n))
    if len(sig_t) >= len(sig_n):
        return completo
    # Nome incompleto: só conta se as palavras citadas não forem genéricas.
    distintivas = [p for p in sig_t if p not in GENERICAS]
    if not distintivas or any(len(p) < 3 for p in distintivas):
        return completo
    parcial = float(fuzz.token_set_ratio(" ".join(sig_t), " ".join(sig_n)))
    cobertura = len(sig_t) / len(sig_n)
    return max(completo, parcial * (0.82 + 0.18 * cobertura))


def resolver_disciplina(pergunta: str, catalogo: Iterable[tuple[int, str]]) -> Optional[Resolucao]:
    """catalogo: (id, nome) das turmas que o usuário pode ver. Devolve None
    quando a pergunta não cita disciplina nenhuma."""
    catalogo = list(catalogo)
    explicito = _termo_explicito(pergunta)
    trechos = janelas(pergunta) + ([explicito] if explicito else [])
    melhores: dict[int, tuple[Opcao, str]] = {}
    for tid, nome in catalogo:
        for t in trechos:
            pts = pontuar_disciplina(t, nome)
            if pts and (tid not in melhores or pts > melhores[tid][0].pontos):
                melhores[tid] = (Opcao(tid, nome, pts), t)
    pontuados = [p for p in melhores.values() if p[0].pontos >= config.FUZZY_SUGESTAO - 15]
    return _decidir("disciplina", pontuados, explicito)


_CODIGO = re.compile(r"\b([a-z]{1,3}\d{2})\b")


def resolver_pessoa(pergunta: str, catalogo: Iterable[tuple[int, str, str]],
                    tipo: str = "aluno") -> Optional[Resolucao]:
    """catalogo: (id, nome, detalhe). Para alunos, o detalhe traz o código da
    matrícula e a disciplina, que também é aceito como referência (A01)."""
    catalogo = list(catalogo)
    texto = normalizar(pergunta)
    tk = [p for p in texto.split()]
    pontuados: dict[int, tuple[Opcao, str]] = {}

    def anotar(pid: int, nome: str, detalhe: str, pts: float, trecho: str) -> None:
        if pid not in pontuados or pts > pontuados[pid][0].pontos:
            pontuados[pid] = (Opcao(pid, nome, pts, detalhe), trecho)

    codigos = set(_CODIGO.findall(texto))
    for pid, nome, detalhe in catalogo:
        if codigos and any(c in normalizar(detalhe).split() for c in codigos):
            anotar(pid, nome, detalhe, 100.0, next(iter(codigos)))
            continue
        partes = normalizar(nome).split()
        primeiro = partes[0]
        for i, p in enumerate(tk):
            if p in PARADAS or len(p) < 3:
                continue
            # primeiro nome sozinho (aceita pequeno erro de digitação)
            r = fuzz.ratio(p, primeiro)
            if r >= 85:
                pts = 86.0 if r == 100 else 76.0
                # nome e sobrenome em seguida valem mais
                if i + 1 < len(tk) and len(partes) > 1:
                    dois = f"{p} {tk[i + 1]}"
                    r2 = max(fuzz.token_sort_ratio(dois, " ".join(partes[:2])),
                             fuzz.token_sort_ratio(dois, f"{primeiro} {partes[-1]}"))
                    if r2 >= 85:
                        pts = max(pts, min(100.0, r2))
                anotar(pid, nome, detalhe, pts, p)
    lista = list(pontuados.values())
    if not lista:
        # Uma referência explícita sem correspondência não é uma consulta
        # geral. Não confundir "alunos com nota baixa" com um nome próprio.
        mencao = re.search(r"\b(?:aluno|aluna|estudante)\s+([a-z]+)", texto)
        if tipo == "aluno" and mencao and mencao.group(1) not in PARADAS:
            return Resolucao(tipo, mencao.group(1), "nenhum")
        return None
    # Mesmo nome com pontuação máxima em mais de uma pessoa: ambíguo.
    return _decidir(tipo, lista)


def escolher_entre(resposta: str, opcoes: list[dict]) -> Optional[dict]:
    """Resposta a uma pergunta de confirmação ('a primeira', 'Estrutura de
    Dados', 'sim'): devolve a opção escolhida ou None."""
    r = normalizar(resposta)
    if not opcoes:
        return None
    if len(opcoes) == 1 and r.split() and r.split()[0] in ("sim", "isso", "essa", "esse", "exato", "pode", "s"):
        return opcoes[0]
    ordinais = {"primeira": 0, "primeiro": 0, "1": 0, "segunda": 1, "segundo": 1, "2": 1,
                "terceira": 2, "terceiro": 2, "3": 2}
    for p in r.split():
        if p in ordinais and ordinais[p] < len(opcoes):
            return opcoes[ordinais[p]]
    melhor, pts = None, 0.0
    for o in opcoes:
        s = max(fuzz.token_set_ratio(r, normalizar(o["nome"])),
                fuzz.token_sort_ratio(r, normalizar(o["nome"])))
        if s > pts:
            melhor, pts = o, s
    return melhor if pts >= config.FUZZY_SUGESTAO else None
