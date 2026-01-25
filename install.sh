#!/usr/bin/env bash

RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

BINARY_NAME="backupctl"
DIST_DIR="$PWD/dist"
BIN_PATH="$DIST_DIR/$BINARY_NAME"

# default install mode: user
INSTALL_MODE="user" # "user" or "system"

error_check() {
  [ $? -eq 0 ] || { printf "%b\n" "${RED}Exiting${NC}"; exit 1; }
}

usage() {
  cat <<EOF
Usage: $0 [--user|--system]

--user   Install to ~/.local/bin (no root) [default]
--system Install to /usr/local/bin (requires sudo)
EOF
}

# Parse args
while [ $# -gt 0 ]; do
  case "$1" in
    --user) INSTALL_MODE="user" ;;
    --system) INSTALL_MODE="system" ;;
    -h|--help) usage; exit 0 ;;
    *) printf "%b\n" "${RED}Unknown option: $1${NC}"; usage; exit 1 ;;
  esac
  shift
done

printf "%b\n" "[*] Checking Python binary path"
python_path="$(command -v python3)" || error_check
venv_dir="venv"
venv_created=0
venv_pre_freeze=""

if [ -d "$venv_dir" ] && [ -f "$venv_dir/bin/activate" ]; then
  printf "%b\n" "[*] ${GREEN}Using existing virtual env at: $venv_dir${NC}"
  source "$venv_dir/bin/activate" || error_check
  venv_pre_freeze="$(python3 -m pip freeze | sort)"
else
  printf "%b\n" "[*] ${YELLOW}No local virtual env found at: $venv_dir${NC}"
  printf "%b\n" "[*] ${YELLOW}Creating a temporary virtual env...${NC}"
  python3 -m venv "$venv_dir" || error_check
  venv_created=1
  source "$venv_dir/bin/activate" || error_check
fi

printf "%b\n" "[*] Installing project dependencies"
python3 -m pip install -r requirements.txt >/dev/null || error_check

# Check that PyInstaller is installed (import check)
printf "%b" "[*] Checking if \"PyInstaller\" package is installed... "
if python3 - <<'EOF'
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec("PyInstaller") else 1)
EOF
then
  printf "%b\n" "${GREEN}OK${NC}"
else
  printf "%b\n" "${YELLOW}NOK${NC}"
  printf "%b\n" "[*] ${YELLOW}Installing PyInstaller...${NC}"
  python3 -m pip install -U pyinstaller >/dev/null || error_check
fi

# Build binary
printf "%b\n" "[*] Creating the binary"
pyinstaller backupctl.spec || error_check

# Decide installation target
if [ "$INSTALL_MODE" = "system" ]; then
  INSTALL_DIR="/usr/local/bin"
  INSTALL_CMD=(sudo install -m 0755 "$BIN_PATH" "$INSTALL_DIR/$BINARY_NAME")
else
  INSTALL_DIR="$HOME/.local/bin"
  mkdir -p "$INSTALL_DIR" || error_check
  INSTALL_CMD=(install -m 0755 "$BIN_PATH" "$INSTALL_DIR/$BINARY_NAME")
fi

printf "%b\n" "[*] Installing binary to ${INSTALL_DIR}"
"${INSTALL_CMD[@]}" || error_check

if [ -z "${SKIP_VERIFY:-}" ]; then
  # Verify install
  printf "%b\n" "[*] Verifying installation"
  if command -v "$BINARY_NAME" >/dev/null 2>&1; then
    printf "%b\n" "[*] ${GREEN}Found in PATH: $(command -v "$BINARY_NAME")${NC}"
  else
    printf "%b\n" "${YELLOW}WARNING: $BINARY_NAME not found in PATH. You may need to add ${INSTALL_DIR} to PATH.${NC}"
  fi

  "$INSTALL_DIR/$BINARY_NAME" --help >/dev/null 2>&1
  if [ $? -eq 0 ]; then
    printf "%b\n" "[*] ${GREEN}Binary runs OK (--help succeeded).${NC}"
  else
    printf "%b\n" "${RED}Binary check failed.${NC}"
    exit 1
  fi
else
  printf "%b\n" "[*] Skipping binary verification (SKIP_VERIFY set)"
fi

# Cleanup venv if we created it
if [ "$venv_created" -eq 1 ]; then
  printf "%b\n" "[*] Removing the temporary virtual environment"
  deactivate || error_check
  rm -rf "$venv_dir" || error_check
elif [ -n "$venv_pre_freeze" ]; then
  venv_post_freeze="$(python3 -m pip freeze | sort)"
  new_packages="$(comm -13 <(printf "%s\n" "$venv_pre_freeze") <(printf "%s\n" "$venv_post_freeze") | awk -F'==' '{print $1}')"
  if [ -n "$new_packages" ]; then
    printf "%b\n" "[*] Removing newly installed packages from existing virtual env"
    python3 -m pip uninstall -y $new_packages >/dev/null || error_check
  fi
fi

printf "%b\n" "[*] ${GREEN}Done.${NC}"
