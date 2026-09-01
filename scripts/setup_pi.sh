#!/usr/bin/env bash
# Run this ON the Raspberry Pi Zero W (Raspberry Pi OS Lite recommended — no desktop needed).
set -euo pipefail

echo "== Updating system =="
sudo apt update && sudo apt full-upgrade -y

echo "== Installing Python + venv =="
sudo apt install -y python3-venv python3-pip

echo "== Enabling SPI for the display =="
sudo raspi-config nonint do_spi 0

cat <<'EOF'

Reboot now (sudo reboot), then continue with steps 2-5 in README.md
(display driver, Python environment, OpenSky credentials, location).

EOF
