#!/usr/bin/env bash
# Compila o app Flutter para a web. A API fica no mesmo domínio (/api), por
# isso nenhum endereço precisa ser passado.
set -euo pipefail
cd app
/tmp/flutter/bin/flutter create . --project-name ecossistema_academico --org br.edu.fainor --platforms=web
/tmp/flutter/bin/flutter pub get
/tmp/flutter/bin/flutter build web --release --no-web-resources-cdn
