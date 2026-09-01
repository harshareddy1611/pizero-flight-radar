import os
import sys
import time

import pygame

from .config import load_config
from .opensky_client import OpenSkyClient
from .tracker import Tracker
from .renderer import Renderer


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cfg = load_config(cfg_path)

    os.environ.setdefault("SDL_VIDEODRIVER", "fbcon")
    os.environ.setdefault("SDL_FBDEV", cfg["display"]["fbdev"])
    os.environ.setdefault("SDL_NOMOUSE", "1")

    pygame.init()

    client = OpenSkyClient(
        home_lat=cfg["home"]["lat"],
        home_lon=cfg["home"]["lon"],
        range_km=cfg["radar"]["max_range_km"],
        username=cfg["opensky"]["username"] or None,
        password=cfg["opensky"]["password"] or None,
    )
    tracker = Tracker(
        home_lat=cfg["home"]["lat"],
        home_lon=cfg["home"]["lon"],
        stale_after_s=cfg["opensky"]["stale_after_s"],
        trail_length=cfg["radar"]["trail_length"],
    )
    renderer = Renderer(cfg)

    poll_interval = cfg["opensky"]["poll_interval_s"]
    frame_interval = 1.0 / cfg["display"]["fps"]

    last_poll = 0.0
    aircraft_list = []

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        now = time.monotonic()
        if now - last_poll >= poll_interval:
            last_poll = now
            try:
                raw = client.fetch_aircraft()
                aircraft_list = tracker.update(raw)
            except Exception as exc:
                print(f"OpenSky fetch failed: {exc}", file=sys.stderr)

        renderer.draw(aircraft_list)
        time.sleep(frame_interval)

    pygame.quit()


if __name__ == "__main__":
    main()
