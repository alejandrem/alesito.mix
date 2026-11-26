#!/usr/bin/env bash
set -euo pipefail

# Descarga los pesos del modelo de basic-pitch-rs desde GitHub Releases.
# Uso:
#   ./backend/scripts/update-model.sh            # última release
#   ./backend/scripts/update-model.sh v0.1.0     # release específica
#
# Requiere: gh (GitHub CLI) autenticado o con acceso público, y sha256sum.

REPO="${MODEL_RELEASE_REPO:-alejandrem/basic-pitch-rs}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEST="${MODEL_DEST:-$BACKEND_DIR/models/basic-pitch/icassp-2022}"
TAG="${1:-${MODEL_RELEASE_TAG:-}}"

ASSETS=(
  cqt_kernels.safetensors
  model.safetensors
  model_config.json
  SHA256SUMS
  source_metadata.json
)

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: se requiere 'gh' (GitHub CLI). Instálalo desde https://cli.github.com/" >&2
  exit 1
fi

if ! command -v sha256sum >/dev/null 2>&1; then
  echo "Error: se requiere 'sha256sum' para verificar la descarga." >&2
  exit 1
fi

if [ -z "$TAG" ]; then
  TAG="$(gh release view -R "$REPO" --json tagName --jq '.tagName')"
fi

echo "==> Descargando modelo $REPO@$TAG"
echo "==> Destino: $DEST"
mkdir -p "$DEST"

# Descarga a un directorio temporal y solo reemplaza si el checksum pasa.
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/basic-pitch-model.XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

ARGS=(release download "$TAG" -R "$REPO" --dir "$TMP_DIR" --clobber)
for asset in "${ASSETS[@]}"; do
  ARGS+=(--pattern "$asset")
done

gh "${ARGS[@]}"

echo "==> Verificando checksums"
(
  cd "$TMP_DIR"
  # Verificar solo los assets descargados; SHA256SUMS puede listar archivos
  # que no se publican como assets de la release.
  TMP_SHA="$(mktemp)"
  for asset in "${ASSETS[@]}"; do
    [ "$asset" = "SHA256SUMS" ] && continue
    grep "  ${asset}$" SHA256SUMS >> "$TMP_SHA" || {
      echo "Error: no se encontró checksum para $asset en SHA256SUMS" >&2
      rm -f "$TMP_SHA"
      exit 1
    }
  done
  sha256sum -c "$TMP_SHA"
  rm -f "$TMP_SHA"
)

echo "==> Instalando en $DEST"
for asset in "${ASSETS[@]}"; do
  install -m 0644 "$TMP_DIR/$asset" "$DEST/$asset"
done

echo "==> Modelo actualizado correctamente ($REPO@$TAG)"
echo "    Archivos en: $DEST"
