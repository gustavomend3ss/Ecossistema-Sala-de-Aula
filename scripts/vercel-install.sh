#!/usr/bin/env bash
# Instala o Flutter (canal stable) no ambiente de build da Vercel.
set -euo pipefail
if [ ! -d /tmp/flutter ]; then
  git clone --depth 1 -b stable https://github.com/flutter/flutter.git /tmp/flutter
fi
/tmp/flutter/bin/flutter --version
/tmp/flutter/bin/flutter config --enable-web --no-analytics
