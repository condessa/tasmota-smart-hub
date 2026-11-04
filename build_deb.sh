#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  build_deb.sh — Cria pacote .deb para Tasmota Smart Hub
#  HCsoftware · github.com/condessa
# ─────────────────────────────────────────────────────────────

set -e

APP_NAME="tasmota-smart-hub"
VERSION="1.0.4"
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
if command -v pyinstaller >/dev/null 2>&1; then
    PYINSTALLER="pyinstaller"
else
    echo "  → PyInstaller não encontrado. A instalar com uv..."
    uv tool install pyinstaller
    PYINSTALLER="uv run pyinstaller"
fi

# ── 2. Gerar executável ────────────────────────
echo "[2/6] A compilar com PyInstaller..."
$PYINSTALLER \
    --onefile \
    --windowed \
    --name "$APP_NAME" \
    --add-data "imagens:imagens" \
    --hidden-import PIL._tkinter_finder \
    --icon "imagens/icone.png" \
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
cp imagens/icone.png "${PKG_DIR}${ICON_DIR}/${APP_NAME}.png"

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

# ── 4b. postinst: refrescar o menu ─────────────
cat > "${PKG_DIR}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
exit 0
EOF
chmod 755 "${PKG_DIR}/DEBIAN/postinst"

# ── 5. Ficheiro .desktop ───────────────────────
echo "[5/6] A criar entrada .desktop..."
cat > "${PKG_DIR}${DESKTOP_DIR}/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Tasmota Smart Hub
Comment=${DESCRIPTION}
Exec="${INSTALL_DIR}/${APP_NAME}"
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
