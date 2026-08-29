#!/usr/bin/env bash
#
# Orcanium — one-line install
#   curl -fsSL https://orcanium.com/install.sh | bash
#
set -euo pipefail

REPO="${ORCANIUM_REPO:-https://github.com/orcanium-ai/orcanium-agent.git}"
BRANCH="${ORCANIUM_BRANCH:-main}"
INSTALL_DIR="${ORCANIUM_HOME:-$HOME/.orcanium}"
# pyproject.toml + uv.lock live in the orcanium/ subdir of the checkout
PROJECT_DIR="$INSTALL_DIR/src/orcanium"

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

step "Checking prerequisites..."
command -v git &>/dev/null || fail "git required: https://git-scm.com"
if ! command -v uv &>/dev/null; then
    info "uv not found — installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv &>/dev/null || fail "uv install failed — add ~/.local/bin to PATH and rerun"
fi
info "uv $(uv --version | cut -d' ' -f2)"

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

step "Installing with uv (locked to uv.lock)..."
# uv sync creates the venv at UV_PROJECT_ENVIRONMENT and installs the project
# + all deps hash-verified against orcanium/uv.lock. --locked refuses to
# silently re-resolve from PyPI if the lockfile goes stale.
if UV_PROJECT_ENVIRONMENT="$INSTALL_DIR/venv" uv sync --locked --project "$PROJECT_DIR"; then
    info "Dependencies installed (hash-verified via uv.lock)"
else
    info "Lockfile sync failed — re-resolving (not hash-verified)"
    UV_PROJECT_ENVIRONMENT="$INSTALL_DIR/venv" uv sync --project "$PROJECT_DIR"
fi
info "venv at $INSTALL_DIR/venv"

step "Wiring orcanium launcher..."
# The wheel's console script is broken: this project uses a root-package
# layout (orcanium package == project dir), which setuptools won't ship under
# py-modules. So instead of relying on venv/bin/orcanium from the wheel, write
# a launcher that runs the CLI from the source checkout — same mechanism as
# bin/orcanium. PYTHONPATH is $INSTALL_DIR/src (the clone root) so `orcanium`
# resolves to $INSTALL_DIR/src/orcanium.
cat > "$INSTALL_DIR/venv/bin/orcanium" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="@SRC@${PYTHONPATH:+:$PYTHONPATH}"
exec "@VENV@/bin/python" -m orcanium.cli "$@"
EOF
sed -i.bak \
    -e "s|@SRC@|$INSTALL_DIR/src|" \
    -e "s|@VENV@|$INSTALL_DIR/venv|" \
    "$INSTALL_DIR/venv/bin/orcanium" && rm -f "$INSTALL_DIR/venv/bin/orcanium.bak"
chmod +x "$INSTALL_DIR/venv/bin/orcanium"
info "Launcher at $INSTALL_DIR/venv/bin/orcanium"

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
