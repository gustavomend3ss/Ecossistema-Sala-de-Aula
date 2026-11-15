"""Serve o app Flutter compilado e a API no mesmo endereço, como na Vercel.

Uso (depois de `flutter build web` dentro de app/):
    python scripts/servidor_local.py            # http://localhost:8080
    python scripts/servidor_local.py --porta 9000 --web caminho/para/build/web

O app compilado chama a API em /api no mesmo domínio, então basta abrir o
endereço no navegador.
"""

import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "backend"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument("--web", default=os.path.join(RAIZ, "app", "build", "web"))
    args = parser.parse_args()

    if not os.path.isfile(os.path.join(args.web, "index.html")):
        sys.exit(f"Build web não encontrado em {args.web}. Rode 'flutter build web' em app/.")

    os.environ.setdefault("SEMEAR_SE_VAZIO", "1")

    import uvicorn
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    from app.main import app as api

    site = FastAPI(docs_url=None, redoc_url=None)
    site.mount("/api", api)
    site.mount("/", StaticFiles(directory=args.web, html=True), name="web")
    print(f"Abra http://localhost:{args.porta}  (senha de todos os usuários: demo123)")
    uvicorn.run(site, host="0.0.0.0", port=args.porta, log_level="warning")


if __name__ == "__main__":
    main()
