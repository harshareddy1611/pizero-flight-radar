import os
import sys
import time

import pygame

from .buttons import ButtonWatcher
from .config import load_config
from .opensky_client import OpenSkyClient
from .tracker import Tracker
from .renderer import Renderer


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cfg = load_config(cfg_path)

    # No real SDL video/audio output is used - Renderer draws to an off-screen
    # surface and writes raw bytes to the framebuffer device itself, and we
    # never play sound. Only initialize the font subsystem (pygame.init() also
    # brings up SDL audio, which spams ALSA underrun warnings on this hardware
    # for no reason since nothing ever plays).
    pygame.font.init()

    client = OpenSkyClient(
        home_lat=cfg["home"]["lat"],
        home_lon=cfg["home"]["lon"],
        range_km=cfg["radar"]["max_range_km"],
        client_id=os.environ.get("OPENSKY_CLIENT_ID"),
        client_secret=os.environ.get("OPENSKY_CLIENT_SECRET"),
    )
    tracker = Tracker(
        home_lat=cfg["home"]["lat"],
        home_lon=cfg["home"]["lon"],
        stale_after_s=cfg["opensky"]["stale_after_s"],
        trail_length=cfg["radar"]["trail_length"],
    )
    renderer = Renderer(cfg)

    try:
        buttons = ButtonWatcher()
    except Exception as exc:
        print(f"Button GPIO unavailable, physical buttons disabled: {exc}", file=sys.stderr)
        buttons = None

    poll_interval = cfg["opensky"]["poll_interval_s"]
    frame_interval = 1.0 / cfg["display"]["fps"]

    last_poll = 0.0
    aircraft_list = []

    while True:
        force_poll = False
        if buttons is not None:
            for button in buttons.poll_events():
                if button == "A":
                    renderer.zoom_in()
                elif button == "B":
                    renderer.zoom_out()
                elif button == "C":
                    force_poll = True
                elif button == "D":
                    renderer.toggle_labels()
                if button in ("A", "B"):
                    client.range_km = renderer.max_range_km
                    force_poll = True

        now = time.monotonic()
        if force_poll or now - last_poll >= poll_interval:
            last_poll = now
            try:
                raw = client.fetch_aircraft()
                aircraft_list = tracker.update(raw)
            except Exception as exc:
                print(f"OpenSky fetch failed: {exc}", file=sys.stderr)

        renderer.draw(aircraft_list)
        time.sleep(frame_interval)


if __name__ == "__main__":
    main()
