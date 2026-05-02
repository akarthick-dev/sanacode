#!/bin/bash

echo "Installing SanaCode CLI..."

INSTALL_DIR="$HOME/.sanacode"

mkdir -p "$INSTALL_DIR"

echo "Installing system dependencies..."
sudo pacman -S --needed unzip python python-pip --noconfirm 2>/dev/null || true

echo "Downloading SanaCode..."
curl -fsSL https://github.com/akarthick-dev/sanacode/archive/refs/heads/main.zip -o /tmp/sanacode.zip

unzip -o /tmp/sanacode.zip -d /tmp/

cp -r /tmp/sanacode-main/* "$INSTALL_DIR"

echo "Installing Python dependencies..."
python3 -m pip install --break-system-packages -r "$INSTALL_DIR/requirements.txt"

echo "Creating CLI command..."
echo '#!/bin/bash
python3 $HOME/.sanacode/main.py "$@"' > "$INSTALL_DIR/sanacode"

chmod +x "$INSTALL_DIR/sanacode"

sudo ln -sf "$INSTALL_DIR/sanacode" /usr/local/bin/sanacode

echo ""
echo "✅ SanaCode installed!"
echo "👉 Run: sanacode"
echo "👉 First run will ask for API key"