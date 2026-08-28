#!/usr/bin/env bash
#
# Orcanium — one-line install
#   curl -fsSL https://orcanium.com/install.sh | bash
#
set -euo pipefail

REPO="${ORCANIUM_REPO:-https://github.com/orcanium/orcanium.git}"
BRANCH="${ORCANIUM_BRANCH:-main}"
INSTALL_DIR="${ORCANIUM_HOME:-$HOME/.orcanium}"
PYTHON="${ORCANIUM_PYTHON:-python3}"

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { printf "${GREEN}✓${NC} %s\n" "$*"; }
step()  { printf "${BOLD}==>${NC} %s\n" "$*"; }
fail()  { printf "${RED}✗${NC} %s\n" "$*"; exit 1; }

step "Orcanium Installer"
echo "  Target:  $INSTALL_DIR"
echo ""

step "Checking Python..."
if ! command -v "$PYTHON" &>/dev/null; then
    fail "Python 3.11+ required: https://python.org"
fi
# grep -oE for portability (BSD grep on macOS lacks -P / PCRE)
PY_VER=$("$PYTHON" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
if awk "BEGIN {exit !($PY_VER < 3.11)}"; then
    fail "Python 3.11+ required (found $PY_VER)"
fi
info "Python $PY_VER"

step "Checking git and pip..."
command -v git  &>/dev/null || fail "git required: https://git-scm.com"
"$PYTHON" -m pip --version &>/dev/null || fail "pip required (python -m ensurepip)"
info "git and pip available"

step "Setting up directory structure..."
mkdir -p "$INSTALL_DIR"/{data/{agents,sessions,gateway},bin}
info "Created $INSTALL_DIR"

step "Fetching source..."
if [ -d "$INSTALL_DIR/src/.git" ]; then
    # Update existing checkout. Pull requires <remote> <refspec>; passing just
    # a branch name makes git interpret it as a remote, which silently fails.
    git -C "$INSTALL_DIR/src" fetch --depth 1 origin "$BRANCH"
    git -C "$INSTALL_DIR/src" reset --hard "origin/$BRANCH"
else
    rm -rf "$INSTALL_DIR/src"
    git clone --depth 1 --branch "$BRANCH" "$REPO" "$INSTALL_DIR/src"
fi
info "Repository ready"

step "Creating virtual environment..."
if [ ! -x "$INSTALL_DIR/venv/bin/python" ]; then
    "$PYTHON" -m venv "$INSTALL_DIR/venv"
fi
info "venv at $INSTALL_DIR/venv"

step "Installing dependencies..."
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -e "$INSTALL_DIR/src/orcanium/"
info "Dependencies installed"

step "Verifying entry point..."
if [ ! -x "$INSTALL_DIR/venv/bin/orcanium" ]; then
    fail "pip install succeeded but $INSTALL_DIR/venv/bin/orcanium is missing"
fi
info "Entry point at $INSTALL_DIR/venv/bin/orcanium"

step "Seeding config..."
CONFIG_EXAMPLE="$INSTALL_DIR/src/orcanium/cli-config.yaml.example"
if [ -f "$CONFIG_EXAMPLE" ] && [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    cp "$CONFIG_EXAMPLE" "$INSTALL_DIR/config.yaml"
    chmod 600 "$INSTALL_DIR/config.yaml"
    info "Seeded $INSTALL_DIR/config.yaml (chmod 600)"
fi

step "Wiring orcanium into PATH..."
SHELL_CONFIG=""
if [[ "${SHELL:-}" == *"zsh"* ]] && [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [[ "${SHELL:-}" == *"bash"* ]] && [ -f "$HOME/.bashrc" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_CONFIG="$HOME/.bash_profile"
fi

if [ -n "$SHELL_CONFIG" ]; then
    if ! grep -q "ORCANIUM_HOME\|/orcanium/venv/bin" "$SHELL_CONFIG" 2>/dev/null; then
        {
            echo ""
            echo "# Orcanium — ensure $INSTALL_DIR/venv/bin is on PATH"
            echo "export ORCANIUM_HOME=\"$INSTALL_DIR\""
            echo 'export PATH="$ORCANIUM_HOME/venv/bin:$PATH"'
        } >> "$SHELL_CONFIG"
        info "Added PATH export to $SHELL_CONFIG"
    else
        info "PATH already configured in $SHELL_CONFIG"
    fi
fi

echo ""
step "Orcanium installed!"
echo ""
echo "  ${BOLD}Quick start:${NC}"
echo "    orcanium setup"
echo "    orcanium gateway"
echo "    orcanium doctor"
echo ""
echo "  ${BOLD}Reload your shell:${NC}"
echo "    source ${SHELL_CONFIG:-$HOME/.zshrc}"
echo ""
echo "  ${BOLD}Docs:${NC}  https://orcanium.com/docs"
