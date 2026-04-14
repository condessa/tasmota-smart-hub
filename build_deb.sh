#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  build_deb.sh — Cria pacote .deb para Tasmota Smart Hub
#  HCsoftware · github.com/condessa
# ─────────────────────────────────────────────────────────────

set -e

APP_NAME="tasmota-smart-hub"
VERSION="1.0.0"
ARCH="amd64"
MAINTAINER="HCsoftware <hcsoftware@email.com>"
DESCRIPTION="Gestão de dispositivos IoT Tasmota via MQTT"
INSTALL_DIR="/opt/HCsoftware/Tasmota Smart Hub"
DESKTOP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/pixmaps"

PKG_DIR="deb_build/${APP_NAME}_${VERSION}_${ARCH}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Tasmota Smart Hub — Build .deb v${VERSION}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Verificar dependências ──────────────────
echo "[1/6] A verificar dependências..."
command -v pyinstaller >/dev/null 2>&1 || {
    echo "  → PyInstaller não encontrado. A instalar..."
    uv tool install pyinstaller
}

# ── 2. Gerar executável ────────────────────────
echo "[2/6] A compilar com PyInstaller..."
uv run pyinstaller \
    --onefile \
    --windowed \
    --name "$APP_NAME" \
    --add-data "imagens:imagens" \
    --icon "imagens/HCsoftware.png" \
    main.py

# ── 3. Criar estrutura do pacote ───────────────
echo "[3/6] A criar estrutura do pacote .deb..."
rm -rf deb_build
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}${INSTALL_DIR}"
mkdir -p "${PKG_DIR}${DESKTOP_DIR}"
mkdir -p "${PKG_DIR}${ICON_DIR}"
mkdir -p "${PKG_DIR}/usr/local/bin"

# Copiar binário
cp "dist/${APP_NAME}" "${PKG_DIR}${INSTALL_DIR}/${APP_NAME}"
chmod +x "${PKG_DIR}${INSTALL_DIR}/${APP_NAME}"

# Copiar ícone
cp imagens/HCsoftware.png "${PKG_DIR}${ICON_DIR}/${APP_NAME}.png"

# Symlink em /usr/local/bin
ln -sf "${INSTALL_DIR}/${APP_NAME}" \
       "${PKG_DIR}/usr/local/bin/${APP_NAME}"

# ── 4. Ficheiro control ────────────────────────
echo "[4/6] A gerar DEBIAN/control..."
cat > "${PKG_DIR}/DEBIAN/control" <<EOF
Package: ${APP_NAME}
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Depends: libc6 (>= 2.17)
Section: utils
Priority: optional
Homepage: https://github.com/condessa/tasmota-smart-hub
Description: ${DESCRIPTION}
 Aplicação desktop para monitorização e controlo de dispositivos
 Tasmota via MQTT. Interface dark-theme HCsoftware com suporte
 a comandos, rules, log MQTT e configuração de broker.
EOF

# ── 5. Ficheiro .desktop ───────────────────────
echo "[5/6] A criar entrada .desktop..."
cat > "${PKG_DIR}${DESKTOP_DIR}/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Tasmota Smart Hub
Comment=${DESCRIPTION}
Exec=${INSTALL_DIR}/${APP_NAME}
Icon=${APP_NAME}
Terminal=false
Categories=Utility;Network;
Keywords=tasmota;mqtt;iot;home automation;
EOF

# ── 6. Construir .deb ──────────────────────────
echo "[6/6] A construir pacote .deb..."
dpkg-deb --build "${PKG_DIR}"

DEB_FILE="${APP_NAME}_${VERSION}_${ARCH}.deb"
mv "deb_build/${DEB_FILE}" .

# Limpeza
rm -rf deb_build dist build __pycache__ *.spec

echo ""
echo "✅  Pacote criado: ${DEB_FILE}"
echo ""
echo "   Instalar:    sudo dpkg -i ${DEB_FILE}"
echo "   Executar:    ${APP_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
