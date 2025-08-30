#!/usr/bin/env bash
set -euo pipefail

# Copia el estado de main2 a itbot_beta como respaldo.

current_branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$current_branch" != "main2" ]]; then
  echo "Debes estar en main2. Rama actual: $current_branch"
  exit 1
fi

git fetch --all --prune

# Verificar que el working tree esté limpio
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Hay cambios sin commit. Haz commit o stash antes de checkpoint."
  exit 1
fi

echo "Creando checkpoint: main2 -> itbot_beta"
git push origin main2:itbot_beta --force-with-lease
echo "Listo. itbot_beta ahora apunta a $(git rev-parse --short HEAD)"
