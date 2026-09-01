import queue
import threading

import requests

AIRCRAFT_URL = "https://hexdb.io/api/v1/aircraft/{hex_id}"
ROUTE_URL = "https://hexdb.io/api/v1/route/icao/{callsign}"


class AircraftInfoLookup:
    """Best-effort background enrichment (aircraft type, route) via hexdb.io.

    Runs lookups on a single worker thread so a slow/unreachable request never
    stalls the render loop - results are written onto the TrackedAircraft
    object once available and just show up on the next frame.
    """

    def __init__(self, timeout_s=5.0):
        self._timeout_s = timeout_s
        self._aircraft_cache = {}
        self._route_cache = {}
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def request(self, entry):
        self._queue.put(entry)

    def _worker(self):
        while True:
            entry = self._queue.get()
            try:
                self._apply_aircraft_type(entry)
                self._apply_route(entry)
            except Exception:
                pass

    def _apply_aircraft_type(self, entry):
        if entry.hex_id not in self._aircraft_cache:
            self._aircraft_cache[entry.hex_id] = self._fetch(AIRCRAFT_URL.format(hex_id=entry.hex_id))
        data = self._aircraft_cache[entry.hex_id]
        if data and "ICAOTypeCode" in data:
            entry.aircraft_type = data["ICAOTypeCode"]
            entry.operator = data.get("RegisteredOwners")

    def _apply_route(self, entry):
        callsign = (entry.flight or "").strip()
        if not callsign:
            return
        if callsign not in self._route_cache:
            self._route_cache[callsign] = self._fetch(ROUTE_URL.format(callsign=callsign))
        data = self._route_cache[callsign]
        if data and "route" in data:
            entry.route = data["route"]

    def _fetch(self, url):
        try:
            resp = requests.get(url, timeout=self._timeout_s)
            data = resp.json()
        except Exception:
            return None
        if not isinstance(data, dict) or "error" in data:
            return None
        return data
