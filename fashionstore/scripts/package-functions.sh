#!/usr/bin/env bash
# Build one zip per Lambda into build/functions/<name>.zip:
#   function code (no tests) + functions/common/fashionstore_common + pip deps
# Deps are installed for linux arm64 / Python 3.12 to match the Lambda runtime.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/build/functions"
PYVER="${LAMBDA_PYTHON_VERSION:-3.12}"
mkdir -p "$OUT"

for dir in "$ROOT"/functions/*/; do
  name="$(basename "$dir")"
  [ "$name" = "common" ] && continue
  stage="$(mktemp -d)"
  trap 'rm -rf "$stage"' EXIT

  # Python copying works on macOS and Linux and fails immediately on copy errors.
  python3 - "$dir" "$ROOT/functions/common/fashionstore_common" "$stage" <<'PY'
from pathlib import Path
import shutil, sys

src, common, stage = map(Path, sys.argv[1:])
shutil.copytree(src, stage, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc", "README.md", ".*"))
shutil.copytree(common, stage / "fashionstore_common",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "testing.py"))
if not (stage / "handler.py").is_file():
    raise SystemExit(f"Missing Lambda handler: {src / 'handler.py'}")
PY

  if grep -qvE '^\s*(#|$)' "$dir/requirements.txt" 2>/dev/null; then
    python3 -m pip install --quiet --disable-pip-version-check \
      --platform manylinux2014_aarch64 --implementation cp --python-version "$PYVER" \
      --only-binary=:all: --no-compile --target "$stage" -r "$dir/requirements.txt"
  fi

  # Deterministic zip (fixed timestamps, sorted entries) so source_code_hash
  # only changes when the code does.
  python3 - "$stage" "$OUT/$name.zip" <<'PY'
import os, sys, zipfile
src, dst = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for f in sorted(files):
            full = os.path.join(root, f)
            info = zipfile.ZipInfo(os.path.relpath(full, src), date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(full, "rb") as fh:
                z.writestr(info, fh.read())
PY
  rm -rf "$stage"
  trap - EXIT
  echo "built $OUT/$name.zip ($(du -h "$OUT/$name.zip" | cut -f1))"
done
