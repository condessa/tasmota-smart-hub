#!/bin/bash
# =============================================================================
# publicar_github.sh — Tasmota Smart Hub by HCsoftware
# Publica o projeto no GitHub
#
# Uso:
#   chmod +x publicar_github.sh
#   ./publicar_github.sh
# =============================================================================

set -e

REPO_NAME="tasmota-smart-hub"
GITHUB_USER="condessa"
GITHUB_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
GITHUB_TOKEN=""  

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Tasmota Smart Hub — Publicar GitHub    ║"
echo "║   by HCsoftware                          ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Verificar git ──────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
    echo "ERRO: git não encontrado. Execute: sudo apt install git"
    exit 1
fi

# ── Verificar token GitHub ─────────────────────────────────────────────────
if [ -z "${GITHUB_TOKEN}" ]; then
    echo "Token GitHub não encontrado."
    echo -n "  Insere o teu GitHub Personal Access Token: "
    read -s GITHUB_TOKEN
    echo ""
fi

if [ -z "${GITHUB_TOKEN}" ]; then
    echo "ERRO: Token necessário para criar o repositório."
    echo ""
    echo "Para criar um token:"
    echo "  1. Vai a https://github.com/settings/tokens"
    echo "  2. Generate new token (classic)"
    echo "  3. Seleciona: repo (full control)"
    echo "  4. Copia o token e cola aqui"
    exit 1
fi

# ── Criar repositório no GitHub via API ───────────────────────────────────
echo "[ 1/4 ] A criar repositório ${REPO_NAME} no GitHub..."

HTTP_CODE=$(curl -s -o /tmp/gh_response.json -w "%{http_code}" \
    -X POST \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/user/repos \
    -d "{
        \"name\": \"${REPO_NAME}\",
        \"description\": \"Gestão de dispositivos IoT Tasmota via MQTT — HCsoftware\",
        \"homepage\": \"https://github.com/${GITHUB_USER}/${REPO_NAME}\",
        \"private\": false,
        \"has_issues\": true,
        \"has_projects\": false,
        \"has_wiki\": false
    }")

if [ "${HTTP_CODE}" = "201" ]; then
    echo "  ✓ Repositório criado: https://github.com/${GITHUB_USER}/${REPO_NAME}"
elif [ "${HTTP_CODE}" = "422" ]; then
    echo "  ℹ Repositório já existe — a continuar com push..."
else
    echo "  ERRO HTTP ${HTTP_CODE}:"
    cat /tmp/gh_response.json
    exit 1
fi

# ── Inicializar git local ──────────────────────────────────────────────────
echo "[ 2/4 ] A inicializar repositório local..."

if [ ! -d ".git" ]; then
    git init
    echo "  ✓ git init"
fi

# .gitignore
if [ ! -f ".gitignore" ]; then
    cat > .gitignore <<'EOF'
__pycache__/
*.py[cod]
*.pyo
.venv/
.uv/
dist/
build/
*.spec
deb_build/
*.deb
tasmota_mqtt_config.json
.DS_Store
Thumbs.db
*.swp
*~
EOF
    echo "  ✓ .gitignore criado"
fi

# Configurar remote com token
if git remote get-url origin &>/dev/null; then
    git remote set-url origin "https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
else
    git remote add origin "https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
fi
echo "  ✓ Remote configurado"

# ── Adicionar ficheiros ────────────────────────────────────────────────────
echo "[ 3/4 ] A preparar ficheiros para commit..."

git add main.py
git add README.md
git add requirements.txt
git add .gitignore


# Pasta imagens (logo)
if [ -d "imagens" ]; then
    git add imagens/
    echo "  ✓ imagens/ incluída"
fi

git status --short
echo ""

# ── Commit e push ──────────────────────────────────────────────────────────
echo "[ 4/4 ] A publicar no GitHub..."

git config user.email "hcsoftware@users.noreply.github.com"
git config user.name "HCsoftware"

git commit -m "🚀 Initial release — Tasmota Smart Hub v1.0.0

- Monitorização de dispositivos Tasmota via MQTT
- Deteção automática online/offline via LWT
- Comandos organizados por categoria (Power, Luz, Timers, Sistema, Rede)
- Gestão de Rules (Rule1/2/3) — consultar, editar, ativar, apagar
- Log MQTT recolhível com histórico enviados/recebidos
- Comando personalizado livre
- Configuração de broker persistente (host, porta, user, pass)
- Tema dark HCsoftware (accent #4a90d9)
- Pacote .deb para Debian/Ubuntu" 2>/dev/null || \
git commit -m "🔄 Update Tasmota Smart Hub"

git branch -M main
git push -u origin main --force

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✓ Publicado com sucesso!                           ║"
echo "╠══════════════════════════════════════════════════════╣"
printf "║  🌐 https://github.com/%-30s ║\n" "${GITHUB_USER}/${REPO_NAME}"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
