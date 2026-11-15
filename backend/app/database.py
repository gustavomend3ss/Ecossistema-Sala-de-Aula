import threading

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config


class Base(DeclarativeBase):
    pass


def criar_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
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
        Base.metadata.create_all(bind=engine)
        if config.SEMEAR_SE_VAZIO:
            from .models import Usuario
            with SessionLocal() as db:
                vazio = db.query(Usuario.id).first() is None
            if vazio:
                from .seed import carregar
                carregar(recriar=False)
        _pronto = True


def get_db():
    garantir_banco()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
