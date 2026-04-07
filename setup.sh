#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_DIR="${SCRIPT_DIR}"

ETH_IF="eth0"
WLAN_IF="wlan0"
ETH_IP="192.168.50.1"
ETH_NETMASK="255.255.255.0"
ETH_CIDR="24"
DHCP_START="192.168.50.50"
DHCP_END="192.168.50.150"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this script as root."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "[1/11] Installing system packages..."
apt update
apt install -y \
  git \
  python3 \
  python3-venv \
  python3-pip \
  python3-full \
  python3-gpiozero \
  python3-lgpio \
  dnsmasq \
  ca-certificates \
  i2c-tools \
  python3-smbus \
  ifupdown \
  net-tools \
  libopenjp2-7 \
  libtiff6 \
  iptables-persistent

echo "[2/11] Removing conflicting GPIO backend if present..."
apt remove -y python3-rpi.gpio || true

echo "[3/11] Enabling hardware I2C interface..."
CONFIG_FILE="/boot/config.txt"
if [[ -f "/boot/firmware/config.txt" ]]; then
    CONFIG_FILE="/boot/firmware/config.txt"
fi

if grep -q "dtparam=i2c_arm" "$CONFIG_FILE" 2>/dev/null; then
  sed -i 's/.*dtparam=i2c_arm.*/dtparam=i2c_arm=on/' "$CONFIG_FILE"
else
  echo "dtparam=i2c_arm=on" >> "$CONFIG_FILE"
fi

if ! grep -q "^i2c-dev" /etc/modules; then
  echo "i2c-dev" >> /etc/modules
fi

modprobe i2c-dev || true

echo "[4/11] Setting default gpiozero backend to lgpio..."
cat > /etc/profile.d/spoeltijd_gpio.sh <<'EOF'
export GPIOZERO_PIN_FACTORY=lgpio
EOF
chmod 644 /etc/profile.d/spoeltijd_gpio.sh

echo "[5/11] Checking project files..."
if [[ ! -f "${REPO_DIR}/requirements.txt" || ! -f "${REPO_DIR}/start.py" ]]; then
  echo "Project files not found in ${REPO_DIR}"
  echo "Make sure setup_network.sh is inside the Spoeltijd project directory."
  exit 1
fi

echo "[6/11] Preparing Python package installer..."
python3 -m pip --version >/dev/null

echo "[7/11] Installing Spoeltijd Python dependencies system-wide..."
python3 -m pip install --break-system-packages -r "${REPO_DIR}/requirements.txt"

echo "[8/11] Backing up current network configuration..."
cp -a /etc/network/interfaces "/etc/network/interfaces.bak.$(date +%F-%H%M%S)" || true

echo "[9/11] Writing network configuration..."
cat > /etc/network/interfaces <<EOF
auto lo
iface lo inet loopback

allow-hotplug ${WLAN_IF}
iface ${WLAN_IF} inet dhcp
    wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf
    metric 100

allow-hotplug ${ETH_IF}
iface ${ETH_IF} inet static
    address ${ETH_IP}
    netmask ${ETH_NETMASK}
    metric 200
EOF

mkdir -p /etc/dnsmasq.d
cat > /etc/dnsmasq.d/spoeltijd-eth0.conf <<EOF
interface=${ETH_IF}
bind-interfaces
listen-address=127.0.0.1,${ETH_IP}
dhcp-range=${DHCP_START},${DHCP_END},255.255.255.0,12h
dhcp-option=6,${ETH_IP}
EOF

echo "[10/11] Applying eth0 configuration now..."
systemctl stop dnsmasq || true

if command -v ifdown >/dev/null 2>&1 && command -v ifup >/dev/null 2>&1; then
  ifdown "${ETH_IF}" 2>/dev/null || true
  ifup "${ETH_IF}" || true
fi

ip link set "${ETH_IF}" up || true
ip addr flush dev "${ETH_IF}" || true
ip addr add "${ETH_IP}/${ETH_CIDR}" dev "${ETH_IF}" || true

echo "[11/11] Enabling DHCP and transparent HTTP proxy..."
systemctl enable dnsmasq
systemctl restart dnsmasq

if grep -q '^net.ipv4.ip_forward=' /etc/sysctl.conf; then
  sed -i 's/^net.ipv4.ip_forward=.*/net.ipv4.ip_forward=1/' /etc/sysctl.conf
else
  echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
fi
sysctl -p

if ! iptables -t nat -C PREROUTING -i "${ETH_IF}" -p tcp --dport 80 -j REDIRECT --to-port 8080 2>/dev/null; then
  iptables -t nat -A PREROUTING -i "${ETH_IF}" -p tcp --dport 80 -j REDIRECT --to-port 8080
fi

netfilter-persistent save

echo
echo "=========================================="
echo "Done. Reboot is required."
echo
echo "After reboot:"
echo "  cd ${REPO_DIR}"
echo "  python3 start.py"
echo
echo "Current network status:"
ip -4 addr show "${WLAN_IF}" || true
ip -4 addr show "${ETH_IF}" || true
echo
echo "dnsmasq status:"
systemctl --no-pager --full status dnsmasq || true
echo
echo "The retro PC can now be connected to ${ETH_IF}."
echo "It should get an IP address automatically by DHCP."
echo "Raspberry Pi Ethernet IP: ${ETH_IP}"
echo "=========================================="