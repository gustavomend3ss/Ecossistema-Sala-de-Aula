"""Carrega dados FICTÍCIOS de demonstração. Apaga e recria o banco.

Uso:  python -m app.seed

Turma de IA: A01, A02 e A03 com notas e frequência exatamente como no
Quadro 7 do Bloco 2. No Bloco 3 entraram atividades com prazo: A02 deixou
duas vencerem sem entrega e passa a acionar R6.
Turma de Web: casos extras, incluindo a fronteira do T02 (média 6,0 e 80%).
Os prazos são relativos à data de hoje, para a demonstração ter sempre
atividades vencidas e em aberto.
Outra professora com turma própria serve para testar o bloqueio do T06.
Estrutura de Dados e Computação Gráfica entraram com o assistente híbrido:
a primeira tem estudantes com baixo desempenho e com muitas faltas (para a
conversa com continuação) e uma segunda "Ana", para a desambiguação; a
segunda acabou de começar e ainda não tem notas nem aulas registradas.
Senha de todos os usuários de demonstração: demo123
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import MetaData

from .database import Base, SessionLocal, engine
from . import config
from .models import (Atividade, Aula, Avaliacao, Criterio, Entrega, Matricula,
                     Nota, Presenca, Turma, Usuario, VinculoProfessorTurma)
from .seguranca import gerar_hash

SENHA = "demo123"


def _datas(inicio: date, quantidade: int) -> list[str]:
    """Terças e quintas a partir da data inicial."""
    datas, d = [], inicio
    while len(datas) < quantidade:
        if d.weekday() in (1, 3):
            datas.append(d.isoformat())
        d += timedelta(days=1)
    return datas


def _usuario(db, login, nome, perfil, hash_):
    u = Usuario(login=login, nome=nome, perfil=perfil, senha_hash=hash_)
    db.add(u)
    db.flush()
    return u


def _turma(db, disciplina, periodo, descricao, criterio, avaliacoes, n_aulas, temas):
    t = Turma(disciplina=disciplina, periodo=periodo, descricao=descricao,
              criterio_id=criterio.id)
    db.add(t)
    db.flush()
    for i, (nome, peso) in enumerate(avaliacoes, start=1):
        db.add(Avaliacao(turma_id=t.id, nome=nome, peso=peso, ordem=i))
    for i, data in enumerate(_datas(date(2026, 8, 4), n_aulas), start=1):
        db.add(Aula(turma_id=t.id, data=data, tema=temas[(i - 1) % len(temas)],
                    unidades=1, ordem=i))
    db.flush()
    db.refresh(t)
    return t


def _matricular(db, turma, aluno, codigo, notas, presentes, sem_registro=0):
    """notas: lista na ordem das avaliações (None = não lançada).
    presentes: quantas aulas com presença; o resto é falta.
    sem_registro: últimas N aulas sem presença lançada (gera pendência R4)."""
    m = Matricula(codigo=codigo, turma_id=turma.id, aluno_id=aluno.id, versao_registros=1)
    db.add(m)
    db.flush()
    for av, valor in zip(turma.avaliacoes, notas):
        if valor is not None:
            db.add(Nota(matricula_id=m.id, avaliacao_id=av.id, valor=valor))
    aulas = turma.aulas
    registradas = aulas[:len(aulas) - sem_registro] if sem_registro else aulas
    # Faltas distribuídas ao longo do semestre, não todas no fim
    faltas = len(registradas) - presentes
    idx_faltas = set()
    if faltas > 0:
        passo = len(registradas) / faltas
        idx_faltas = {int(i * passo + passo / 2) for i in range(faltas)}
    for i, aula in enumerate(registradas):
        db.add(Presenca(matricula_id=m.id, aula_id=aula.id, presente=i not in idx_faltas))
    return m


def _atividades(db, turma, lista):
    """lista: (título, descrição, dias em relação a hoje)."""
    hoje = config.hoje()
    criadas = []
    for titulo, descricao, dias in lista:
        a = Atividade(turma_id=turma.id, titulo=titulo, descricao=descricao,
                      prazo=(hoje + timedelta(days=dias)).isoformat())
        db.add(a)
        criadas.append(a)
    db.flush()
    return criadas


def _entregar(db, m, atividade, atraso_dias=0):
    """Entrega no prazo (atraso 0 = um dia antes) ou com atraso em dias."""
    prazo = date.fromisoformat(atividade.prazo)
    dia = prazo + timedelta(days=atraso_dias) if atraso_dias > 0 else prazo - timedelta(days=1)
    db.add(Entrega(matricula_id=m.id, atividade_id=atividade.id, entregue_em=dia.isoformat()))


def carregar(recriar: bool = True) -> None:
    if recriar:
        # Reflete o banco antes de apagar: assim saem também tabelas de versões
        # anteriores (como "sessao", da v0.1) que o modelo atual não conhece.
        antigo = MetaData()
        antigo.reflect(bind=engine)
        antigo.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    h = gerar_hash(SENHA)   # mesmo hash para todos agiliza o seed (só demonstração)

    # DEMO-v2 = DEMO-v1 do Bloco 2 (média 6,0 e frequência 80%) + limite de
    # entregas (R6), que entrou no Bloco 3.
    demo = Criterio(versao="DEMO-v2", media_minima=6.0, frequencia_minima=80.0,
                    atrasos_maximos=1,
                    descricao="Limites didáticos de demonstração; não são critérios oficiais da FAINOR.")
    db.add(demo)
    db.flush()

    gabriel = _usuario(db, "prof.gabriel", "Prof. Gabriel", "professor", h)
    helena = _usuario(db, "prof.helena", "Profa. Helena", "professor", h)

    temas_ia = ["Agentes racionais", "Busca em largura", "Busca em profundidade",
                "Custo uniforme", "Busca gulosa", "Algoritmo A*", "Lógica proposicional",
                "Lógica de primeira ordem", "Redes semânticas", "Frames",
                "Fatores de certeza", "Sistemas especialistas"]
    ia = _turma(db, "Inteligência Artificial", "2026.2", "Turma demonstrativa", demo,
                [("Avaliação 1", 1.0), ("Avaliação 2", 1.0)], 25, temas_ia)

    temas_web = ["HTTP", "Cliente-servidor", "MVC", "UX e dores", "Flutter Web",
                 "Supabase vs. Python", "Rotas e APIs", "Autenticação", "Validação", "Deploy"]
    web = _turma(db, "Desenvolvimento de Sistemas Web", "2026.2", "Turma demonstrativa", demo,
                 [("Bloco 1", 1.0), ("Bloco 2", 1.5), ("Prova parcial", 2.5)], 20, temas_web)

    bd = _turma(db, "Banco de Dados", "2026.2", "Turma de outra docente", demo,
                [("Prova 1", 1.0)], 10, ["Modelagem"])

    temas_ed = ["Listas", "Pilhas", "Filas", "Árvores", "Ordenação", "Hash"]
    ed = _turma(db, "Estrutura de Dados", "2026.2", "Turma demonstrativa", demo,
                [("Prova 1", 1.0), ("Prova 2", 1.0)], 20, temas_ed)
    cg = _turma(db, "Computação Gráfica", "2026.2", "Turma em início de semestre", demo,
                [("Projeto 1", 1.0), ("Projeto 2", 1.0)], 0, ["Pipeline gráfico"])

    for t in (ia, web, ed, cg):
        db.add(VinculoProfessorTurma(professor_id=gabriel.id, turma_id=t.id))
    db.add(VinculoProfessorTurma(professor_id=helena.id, turma_id=bd.id))

    ana = _usuario(db, "ana.lima", "Ana Lima", "aluno", h)
    bruno = _usuario(db, "bruno.reis", "Bruno Reis", "aluno", h)
    carla = _usuario(db, "carla.dias", "Carla Dias", "aluno", h)
    diego = _usuario(db, "diego.santos", "Diego Santos", "aluno", h)
    elisa = _usuario(db, "elisa.moura", "Elisa Moura", "aluno", h)
    fabio = _usuario(db, "fabio.costa", "Fábio Costa", "aluno", h)
    gina = _usuario(db, "gina.alves", "Gina Alves", "aluno", h)
    anab = _usuario(db, "ana.souza", "Ana Beatriz Souza", "aluno", h)
    igor = _usuario(db, "igor.matos", "Igor Matos", "aluno", h)
    julia = _usuario(db, "julia.ferraz", "Júlia Ferraz", "aluno", h)

    # Quadro 7 do Bloco 2
    a01 = _matricular(db, ia, ana, "A01", [5.0, 5.4], presentes=19)      # 5,2 e 76% → R1,R2,R3
    a02 = _matricular(db, ia, bruno, "A02", [7.0, 8.0], presentes=23)    # 7,5 e 92%, mas 2 sem entrega → R6
    a03 = _matricular(db, ia, carla, "A03", [7.0, None], presentes=23)   # média não avaliável (R4)

    # Turma de Web: casos complementares
    w01 = _matricular(db, web, diego, "W01", [8.0, 7.5, 7.0], presentes=19)   # 95% sem alerta
    w02 = _matricular(db, web, elisa, "W02", [6.0, 6.0, 6.0], presentes=16)   # 6,0 e 80%: fronteira T02
    w03 = _matricular(db, web, fabio, "W03", [7.0, 6.5, 8.0], presentes=14)   # 70% → R2, e 2 sem entrega → R6
    w04 = _matricular(db, web, gina, "W04", [4.0, 5.5, 5.0], presentes=18, sem_registro=1)  # R1 + presença pendente
    w05 = _matricular(db, web, ana, "W05", [9.0, 8.5, None], presentes=20)    # prova não lançada

    # Estrutura de Dados: baixo desempenho (R1) com e sem muitas faltas (R2)
    _matricular(db, ed, anab, "E01", [4.0, 5.0], presentes=14)    # 4,5 e 70% → R1, R2, R3
    _matricular(db, ed, igor, "E02", [5.0, 5.0], presentes=18)    # 5,0 e 90% → R1
    _matricular(db, ed, diego, "E03", [7.5, 8.0], presentes=19)   # sem alerta
    _matricular(db, ed, bruno, "E04", [5.5, 5.5], presentes=15)   # 5,5 e 75% → R1, R2, R3

    # Computação Gráfica: nada lançado ainda (consulta sem dados)
    for cod, aluno in (("G01", julia), ("G02", fabio), ("G03", elisa)):
        _matricular(db, cg, aluno, cod, [None, None], presentes=0)
    db.flush()

    # Atividades com prazo (Bloco 3)
    l1, l2, mapa, _base = _atividades(db, ia, [
        ("Lista 1: busca cega em Python", "Largura, profundidade e custo uniforme.", -35),
        ("Lista 2: A* e heurísticas", "Implementar A* e comparar heurísticas admissíveis.", -21),
        ("Mapa de frames e redes semânticas", "Representar o domínio acadêmico em frames.", -8),
        ("Base de regras com fatores de certeza", "Escrever regras com FC e testar a combinação.", 6),
    ])
    _entregar(db, a01, l1); _entregar(db, a01, l2, atraso_dias=2); _entregar(db, a01, mapa)
    _entregar(db, a02, l1)                                   # L2 e mapa vencidos sem entrega
    _entregar(db, a03, l1); _entregar(db, a03, l2)           # só o mapa falta (dentro do limite)

    dores, proto, rotas, _deploy = _atividades(db, web, [
        ("Mapa de dores e benchmarking", "Entregável de pesquisa do Bloco 1.", -40),
        ("Protótipo mid-fi das telas", "Fluxo de navegação e telas principais.", -26),
        ("Rotas e modelo de dados da API", "Quadro de rotas REST e entidades.", -12),
        ("Deploy do sistema", "Publicar front-end e API.", 3),
    ])
    for m in (w01, w05):
        _entregar(db, m, dores); _entregar(db, m, proto); _entregar(db, m, rotas)
    _entregar(db, w02, dores); _entregar(db, w02, proto); _entregar(db, w02, rotas, atraso_dias=1)
    _entregar(db, w03, dores)                                # 2 vencidas sem entrega
    _entregar(db, w04, dores); _entregar(db, w04, proto)

    # Turma da outra docente (para o teste de bloqueio)
    _matricular(db, bd, bruno, "B01", [6.5], presentes=10)

    db.commit()
    db.close()


if __name__ == "__main__":
    carregar()
    print("Banco recriado com dados fictícios. Senha de todos os usuários: demo123")
    print("Professor: prof.gabriel  |  Alunos: ana.lima, bruno.reis, carla.dias ...")
