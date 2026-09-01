import time
from collections import deque

from . import geo


class TrackedAircraft:
    def __init__(self, hex_id, trail_length):
        self.hex_id = hex_id
        self.flight = None
        self.alt_baro = None
        self.track = 0.0
        self.distance_km = None
        self.bearing_deg = None
        self.last_seen = time.monotonic()
        self.trail = deque(maxlen=trail_length)

        # Best-effort enrichment from AircraftInfoLookup (aircraft_info.py).
        # Requested once per sighting (info_requested), not re-tried even on a
        # cache miss, to avoid re-queueing the same lookup every poll cycle.
        self.aircraft_type = None
        self.operator = None
        self.route = None
        self.info_requested = False


class Tracker:
    def __init__(self, home_lat, home_lon, stale_after_s, trail_length):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.stale_after_s = stale_after_s
        self.trail_length = trail_length
        self.aircraft = {}

    def update(self, raw_aircraft):
        now = time.monotonic()
        for a in raw_aircraft:
            lat, lon = a.get("lat"), a.get("lon")
            if lat is None or lon is None:
                continue
            hex_id = a.get("hex")
            if hex_id is None:
                continue

            entry = self.aircraft.get(hex_id)
            if entry is None:
                entry = TrackedAircraft(hex_id, self.trail_length)
                self.aircraft[hex_id] = entry

            entry.flight = (a.get("flight") or "").strip() or None
            entry.alt_baro = a.get("alt_baro")
            entry.track = a.get("track") or entry.track
            entry.distance_km = geo.haversine_km(self.home_lat, self.home_lon, lat, lon)
            entry.bearing_deg = geo.bearing_deg(self.home_lat, self.home_lon, lat, lon)
            entry.last_seen = now
            entry.trail.append((entry.distance_km, entry.bearing_deg))

        self._drop_stale(now)
        return list(self.aircraft.values())

    def _drop_stale(self, now):
        stale = [
            hex_id
            for hex_id, entry in self.aircraft.items()
            if now - entry.last_seen > self.stale_after_s
        ]
        for hex_id in stale:
            del self.aircraft[hex_id]
