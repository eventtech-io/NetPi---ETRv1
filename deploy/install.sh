#!/bin/bash
set -e

NETPI_USER="netpi"
NETPI_HOME="/opt/netpi"
SERVICE_NAME="netpi"

echo "=== NetPi Installer ==="
echo "Target: Raspberry Pi 4/5 (arm64)"

# 1. Update system
echo "[1/9] Updating package lists..."
sudo apt-get update

# 2. Install system dependencies
echo "[2/9] Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    libpcap-dev \
    tcpdump \
    tshark \
    ethtool \
    iperf3 \
    speedtest-cli \
    wireshark-common \
    git

# Allow non-root tcpdump
echo "[3/9] Configuring tcpdump capabilities..."
sudo setcap cap_net_raw,cap_net_admin=eip "$(which tcpdump)" || true

# 3. Create netpi user and directory
echo "[4/9] Creating netpi user and directories..."
if ! id "$NETPI_USER" &>/dev/null; then
    sudo useradd -r -s /bin/false -d "$NETPI_HOME" "$NETPI_USER"
fi
sudo mkdir -p "$NETPI_HOME"
sudo mkdir -p /var/lib/netpi/captures
sudo chown -R "$NETPI_USER:$NETPI_USER" "$NETPI_HOME"
sudo chown -R "$NETPI_USER:$NETPI_USER" /var/lib/netpi

# BUG-FIX: add netpi user to dialout group for UART/USB DMX access
# (docs mentioned this but the installer never did it)
echo "[5/9] Adding netpi user to dialout group (required for DMX)..."
sudo usermod -a -G dialout "$NETPI_USER"

# 4. Create virtual environment
echo "[6/9] Creating Python virtual environment..."
sudo -u "$NETPI_USER" python3 -m venv "$NETPI_HOME/venv"

# 5. Install packages
echo "[7/9] Installing NetPi packages..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Copy source (exclude .git and __pycache__ to keep it clean)
sudo rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='*.egg-info' --exclude='.venv' --exclude='venv' \
    "$PROJECT_ROOT/" "$NETPI_HOME/src/"
sudo chown -R "$NETPI_USER:$NETPI_USER" "$NETPI_HOME/src"

VENV_PIP="$NETPI_HOME/venv/bin/pip"
sudo -u "$NETPI_USER" "$VENV_PIP" install --upgrade pip

for pkg in netpi-core netpi-analyzer netpi-cabletester netpi-discovery netpi-tests netpi-dmx netpi-server; do
    echo "  Installing $pkg..."
    sudo -u "$NETPI_USER" "$VENV_PIP" install -e "$NETPI_HOME/src/packages/$pkg"
done

# 6. Install systemd service
echo "[8/9] Installing systemd service..."
sudo cp "$SCRIPT_DIR/netpi.service" /etc/systemd/system/
sudo sed -i "s|/opt/netpi|$NETPI_HOME|g" /etc/systemd/system/netpi.service
sudo systemctl daemon-reload
sudo systemctl enable netpi.service

# 7. Start service
echo "[9/9] Starting NetPi service..."
sudo systemctl start netpi.service

echo ""
echo "=== NetPi installation complete ==="
echo "Service:  sudo systemctl status netpi"
echo "API:      http://$(hostname -I | awk '{print $1}'):8080"
echo "Logs:     sudo journalctl -u netpi -f"
echo ""
echo "Optional: set NETPI_API_KEY in /etc/systemd/system/netpi.service"
echo "          [Service] → Environment=NETPI_API_KEY=your-secret-key"
echo "          then: sudo systemctl daemon-reload && sudo systemctl restart netpi"
