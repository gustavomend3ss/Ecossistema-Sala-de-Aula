import threading

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config


class Base(DeclarativeBase):
    pass


def criar_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Função serverless: poucas conexões por instância e teste antes de usar
        # (o Postgres gerenciado fecha conexões ociosas).
        kwargs.update(pool_pre_ping=True, pool_size=2, max_overflow=3, pool_recycle=300)
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        # SQLite só respeita chave estrangeira com esta opção ligada
        @event.listens_for(eng, "connect")
        def _fk(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return eng


engine = criar_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

_pronto = False
_trava = threading.Lock()


def garantir_banco() -> None:
    """Cria as tabelas na primeira requisição e, se configurado, semeia os
    dados fictícios. Em função sem estado (Vercel) não há evento de início
    confiável, então a verificação acontece aqui, uma vez por instância."""
    global _pronto
    if _pronto:
        return
    with _trava:
        if _pronto:
            return
        from . import models  # noqa: F401  (registra as tabelas)
        if engine.dialect.name == "postgresql":
            # Várias instâncias podem subir juntas. A trava consultiva do
            # Postgres garante que só uma cria as tabelas e semeia por vez.
            with engine.connect() as conn:
                conn.execute(text("SELECT pg_advisory_lock(7310462)"))
                try:
                    _criar_e_semear()
                finally:
                    conn.execute(text("SELECT pg_advisory_unlock(7310462)"))
                    conn.commit()
        else:
            _criar_e_semear()
        _pronto = True


def _criar_e_semear() -> None:
    Base.metadata.create_all(bind=engine)   # só cria o que falta; nunca apaga
    if config.SEMEAR_SE_VAZIO:
        from .models import Usuario
        with SessionLocal() as db:
            vazio = db.query(Usuario.id).first() is None
        if vazio:
            from .seed import carregar
            carregar(recriar=False)


def get_db():
    garantir_banco()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
