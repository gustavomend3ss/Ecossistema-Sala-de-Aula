"""Carrega dados FICTÍCIOS de demonstração. Apaga e recria o banco.

Uso:  python -m app.seed

Turma de IA: A01, A02 e A03 exatamente como no Quadro 7 do Bloco 2.
Turma de Web: casos extras, incluindo a fronteira do T02 (média 6,0 e 80%).
Outra professora com turma própria serve para testar o bloqueio do T06.
Senha de todos os usuários de demonstração: demo123
"""

from __future__ import annotations

from datetime import date, timedelta

from .database import Base, SessionLocal, engine
from .models import (Aula, Avaliacao, Criterio, Matricula, Nota, Presenca,
                     Turma, Usuario, VinculoProfessorTurma)
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


def carregar() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    h = gerar_hash(SENHA)   # mesmo hash para todos agiliza o seed (só demonstração)

    demo = Criterio(versao="DEMO-v1", media_minima=6.0, frequencia_minima=80.0,
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

    for t in (ia, web):
        db.add(VinculoProfessorTurma(professor_id=gabriel.id, turma_id=t.id))
    db.add(VinculoProfessorTurma(professor_id=helena.id, turma_id=bd.id))

    ana = _usuario(db, "ana.lima", "Ana Lima", "aluno", h)
    bruno = _usuario(db, "bruno.reis", "Bruno Reis", "aluno", h)
    carla = _usuario(db, "carla.dias", "Carla Dias", "aluno", h)
    diego = _usuario(db, "diego.santos", "Diego Santos", "aluno", h)
    elisa = _usuario(db, "elisa.moura", "Elisa Moura", "aluno", h)
    fabio = _usuario(db, "fabio.costa", "Fábio Costa", "aluno", h)
    gina = _usuario(db, "gina.alves", "Gina Alves", "aluno", h)

    # Quadro 7 do Bloco 2
    _matricular(db, ia, ana, "A01", [5.0, 5.4], presentes=19)      # 5,2 e 76% → R1,R2,R3
    _matricular(db, ia, bruno, "A02", [7.0, 8.0], presentes=23)    # 7,5 e 92% → sem alerta
    _matricular(db, ia, carla, "A03", [7.0, None], presentes=23)   # média não avaliável (R4)

    # Turma de Web: casos complementares
    _matricular(db, web, diego, "W01", [8.0, 7.5, 7.0], presentes=19)   # 95% sem alerta
    _matricular(db, web, elisa, "W02", [6.0, 6.0, 6.0], presentes=16)   # 6,0 e 80%: fronteira T02
    _matricular(db, web, fabio, "W03", [7.0, 6.5, 8.0], presentes=14)   # 70% → só R2
    _matricular(db, web, gina, "W04", [4.0, 5.5, 5.0], presentes=18, sem_registro=1)  # R1 + presença pendente
    _matricular(db, web, ana, "W05", [9.0, 8.5, None], presentes=20)    # prova não lançada

    # Turma da outra docente (para o teste de bloqueio)
    _matricular(db, bd, bruno, "B01", [6.5], presentes=10)

    db.commit()
    db.close()


if __name__ == "__main__":
    carregar()
    print("Banco recriado com dados fictícios. Senha de todos os usuários: demo123")
    print("Professor: prof.gabriel  |  Alunos: ana.lima, bruno.reis, carla.dias ...")
