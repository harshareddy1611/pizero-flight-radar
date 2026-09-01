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

Next steps (manual, depends on your exact display):
1. Reboot: sudo reboot
2. Identify your SPI display's driver/overlay (search the board's silkscreen model number,
   e.g. "Waveshare 3.5inch RPi LCD (A)"), add the matching dtoverlay line to /boot/firmware/config.txt,
   and reboot. After that /dev/fb1 should exist (check with: ls /dev/fb*).
3. Set display.fbdev in config.yaml to match (usually /dev/fb1), and width/height to your panel's
   native resolution.
4. Create the Python venv and install deps:
     cd ~/live_flight_tracker
     python3 -m venv .venv
     .venv/bin/pip install -r requirements.txt
5. Fill in config.yaml home.lat / home.lon with your receiver's coordinates.
6. Test it manually first:
     .venv/bin/python -m src.flight_tracker.main config.yaml
7. Once it looks right, install the service:
     sudo cp systemd/flight-tracker.service /etc/systemd/system/
     sudo systemctl daemon-reload
     sudo systemctl enable --now flight-tracker.service

EOF
