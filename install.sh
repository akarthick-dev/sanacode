#!/bin/bash

echo "Installing SanaCode CLI..."

INSTALL_DIR="$HOME/.sanacode"

mkdir -p "$INSTALL_DIR"

echo "Installing dependencies..."
sudo pacman -S --needed unzip python python-pip --noconfirm 2>/dev/null || true

echo "Downloading files..."
curl -fsSL https://github.com/akarthick-dev/sanacode/archive/refs/heads/main.zip -o /tmp/sanacode.zip

unzip -o /tmp/sanacode.zip -d /tmp/

cp -r /tmp/sanacode-main/* "$INSTALL_DIR"

if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    python3 -m pip install --user -r "$INSTALL_DIR/requirements.txt"
fi

echo '#!/bin/bash
python3 $HOME/.sanacode/main.py "$@"' > "$INSTALL_DIR/sanacode"

chmod +x "$INSTALL_DIR/sanacode"

sudo ln -sf "$INSTALL_DIR/sanacode" /usr/local/bin/sanacode

echo "✅ Installed successfully!"
echo ""
echo "👉 Run: sanacode"
echo "👉 First run will ask for API key"