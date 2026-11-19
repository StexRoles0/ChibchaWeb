#!/usr/bin/env bash
# Corre toda la suite e2e desde cero en el entorno AISLADO (docker-compose.e2e.yml, proyecto chibchaweb_e2e).
#   npm run e2e                 # recrea la BD e2e, levanta todo, corre Playwright y deja el entorno detenido
#   E2E_MANTENER=1 npm run e2e  # no lo apaga al terminar (para depurar)
#   npm run e2e -- auth-03      # argumentos extra van a `playwright test`
# Nunca toca el proyecto de desarrollo (volumen datos_pg16): solo "chibchaweb_e2e".
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ"
PROYECTO=chibchaweb_e2e
COMPOSE=(docker compose -p "$PROYECTO" -f docker-compose.e2e.yml)

apagar() {
  if [ "${E2E_MANTENER:-0}" = "1" ]; then
    echo ">> E2E_MANTENER=1: el entorno e2e sigue arriba (frontend :14200, API :18000)."
  else
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
    echo ">> Entorno e2e detenido y su BD descartada."
  fi
}
trap apagar EXIT

echo ">> Partiendo limpio: se descarta el proyecto $PROYECTO (solo ese)."
"${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
echo ">> Levantando db, backend y frontend (la primera vez construye las imágenes)."
"${COMPOSE[@]}" up -d --build --wait

cd "$RAIZ/frontend"
npx playwright test "$@"
