# Live Flight Tracker (Raspberry Pi Zero W)

A radar-scope style display of live aircraft overhead, pulled from the free
**OpenSky Network** API over WiFi, rendered directly to a small SPI display —
no desktop environment, no map tiles, no SDR hardware needed. Just the Pi and
a display.

## How it works

1. `src/flight_tracker/opensky_client.py` polls OpenSky Network's free public
   REST API (`/api/states/all`) for a bounding box around your location and
   gets back live aircraft position reports.
2. The app computes each aircraft's distance/bearing from your location, and
   draws a radar screen (range rings, N-up, rotated plane icons with callsign
   + altitude) straight to the framebuffer using `pygame` — headless, on boot,
   no browser or window manager.

No RTL-SDR dongle, no antenna, no USB OTG adapter. Just the Pi Zero W's
built-in WiFi and a small display.

## The tradeoff vs. a local SDR receiver

OpenSky's anonymous API is rate-limited (~400 requests/day), so this project
defaults to polling every 5 minutes (`poll_interval_s: 300` in `config.yaml`) —
aircraft positions update coarsely, not second-by-second. If you want it more
live:

- Register a free account at https://opensky-network.org/ and add your
  `username`/`password` to `config.yaml` under `opensky:` — raises the cap to
  ~4000 requests/day, letting you poll every ~25s.
- Coverage also depends on OpenSky's crowd-sourced ground station network —
  it's very good in most populated areas, but sparser than what a nearby local
  RTL-SDR receiver would see directly overhead.

If you ever do pick up an RTL-SDR dongle + ADS-B antenna later, this design
adapts easily — the OpenSky client would just be swapped for a `dump1090-fa`
client, everything else (tracker, renderer) stays the same.

## Hardware you need

| Part | Notes |
|---|---|
| Raspberry Pi Zero W (v1.1) | what you have |
| Small SPI display (HAT-style, full 40-pin header) | e.g. Waveshare 3.5" ILI9486-class display. Config assumes 480x320 SPI TFT by default — adjust `config.yaml` to match yours. |
| WiFi | already on-board |

## Setup

On the Pi:

```bash
git clone <this repo> ~/live_flight_tracker
cd ~/live_flight_tracker
bash scripts/setup_pi.sh
```

The script installs Python/venv tooling and enables SPI. It prints the manual
steps you still need to do (display driver overlay, venv, config, service)
because those depend on your exact display model — see the script's output.

## Configuration

Edit `config.yaml`:

- `home.lat` / `home.lon` — your location's coordinates (required — this is
  the center of the radar and how distance/bearing to aircraft are computed).
- `opensky.username` / `opensky.password` — optional, but recommended once you
  have a free account (see tradeoff section above).
- `display.width` / `height` / `fbdev` — match your SPI display's resolution
  and framebuffer device (`/dev/fb1` is typical when it's alongside the HDMI
  console).
- `radar.max_range_km` — how far out to show aircraft and size the bounding
  box query.

## Running

Manually, for testing:

```bash
.venv/bin/python -m src.flight_tracker.main config.yaml
```

As a boot-time service:

```bash
sudo cp systemd/flight-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flight-tracker.service
sudo journalctl -u flight-tracker.service -f   # logs
```

## Troubleshooting

- **No aircraft ever show up**: test the API directly first —
  `curl "https://opensky-network.org/api/states/all?lamin=<..>&lomin=<..>&lamax=<..>&lomax=<..>"`
  with a bounding box around your coordinates. An empty `states` list can mean
  genuinely no traffic overhead right now, or coverage gaps in your area.
- **429 / rate limited errors**: you're polling too often for anonymous access
  — raise `poll_interval_s`, or register a free OpenSky account and add
  credentials to `config.yaml`.
- **Screen stays blank**: confirm `/dev/fb1` (or whatever `display.fbdev` points
  to) exists (`ls /dev/fb*`) — if not, the display's kernel driver overlay isn't
  loaded yet in `/boot/firmware/config.txt`.
- **Performance**: keep `display.fps` low (1-2) — the Zero W's CPU is the
  bottleneck, and aircraft positions only update as often as `poll_interval_s`
  allows anyway.
