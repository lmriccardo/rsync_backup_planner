#!/usr/bin/env bash

RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

BINARY_NAME="backupctl"

# default uninstall mode: user
UNINSTALL_MODE="user" # "user" or "system"

error_check() {
  [ $? -eq 0 ] || { printf "%b\n" "${RED}Exiting${NC}"; exit 1; }
}

usage() {
  cat <<EOF
Usage: $0 [--user|--system]

--user   Uninstall from ~/.local/bin (no root) [default]
--system Uninstall from /usr/local/bin (requires sudo)
EOF
}

# Parse args
while [ $# -gt 0 ]; do
  case "$1" in
    --user) UNINSTALL_MODE="user" ;;
    --system) UNINSTALL_MODE="system" ;;
    -h|--help) usage; exit 0 ;;
    *) printf "%b\n" "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
  shift
done

if [ "$UNINSTALL_MODE" = "system" ]; then
  UNINSTALL_DIR="/usr/local/bin"
  UNINSTALL_CMD=(sudo rm -f "$UNINSTALL_DIR/$BINARY_NAME")
else
  UNINSTALL_DIR="$HOME/.local/bin"
  UNINSTALL_CMD=(rm -f "$UNINSTALL_DIR/$BINARY_NAME")
fi

if [ -e "$UNINSTALL_DIR/$BINARY_NAME" ]; then
  printf "%b\n" "[*] Removing ${UNINSTALL_DIR}/${BINARY_NAME}"
  "${UNINSTALL_CMD[@]}" || error_check
  printf "%b\n" "[*] ${GREEN}Uninstalled.${NC}"
else
  printf "%b\n" "${YELLOW}WARNING: ${UNINSTALL_DIR}/${BINARY_NAME} not found.${NC}"
fi
