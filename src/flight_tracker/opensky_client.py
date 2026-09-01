import math
import time

import requests

METERS_TO_FEET = 3.28084

STATE_ICAO24 = 0
STATE_CALLSIGN = 1
STATE_LONGITUDE = 5
STATE_LATITUDE = 6
STATE_BARO_ALTITUDE = 7
STATE_ON_GROUND = 8
STATE_TRUE_TRACK = 10

TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
)
TOKEN_EXPIRY_MARGIN_S = 30


class OpenSkyClient:
    """Fetches nearby aircraft state vectors from the free OpenSky Network REST API.

    Anonymous access is capped around 400 requests/day - keep poll_interval_s high
    unless you register a free OpenSky account and pass an OAuth2 client_id/
    client_secret (from the account's API client page), which raises the cap to
    ~4000/day.
    """

    def __init__(self, home_lat, home_lon, range_km, client_id=None, client_secret=None, timeout_s=10.0):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.range_km = range_km
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout_s = timeout_s
        self._access_token = None
        self._token_expires_at = 0.0

    def _bounding_box(self):
        lat_delta = self.range_km / 111.0
        lon_delta = self.range_km / (111.0 * max(math.cos(math.radians(self.home_lat)), 0.01))
        return {
            "lamin": self.home_lat - lat_delta,
            "lamax": self.home_lat + lat_delta,
            "lomin": self.home_lon - lon_delta,
            "lomax": self.home_lon + lon_delta,
        }

    def _auth_headers(self):
        if not self.client_id or not self.client_secret:
            return {}

        if time.monotonic() < self._token_expires_at:
            return {"Authorization": f"Bearer {self._access_token}"}

        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        token_data = resp.json()
        self._access_token = token_data["access_token"]
        self._token_expires_at = time.monotonic() + token_data["expires_in"] - TOKEN_EXPIRY_MARGIN_S

        return {"Authorization": f"Bearer {self._access_token}"}

    def fetch_aircraft(self):
        resp = requests.get(
            "https://opensky-network.org/api/states/all",
            params=self._bounding_box(),
            headers=self._auth_headers(),
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        states = data.get("states") or []

        aircraft = []
        for s in states:
            if s[STATE_ON_GROUND]:
                continue
            lat, lon = s[STATE_LATITUDE], s[STATE_LONGITUDE]
            if lat is None or lon is None:
                continue
            baro_alt_m = s[STATE_BARO_ALTITUDE]
            aircraft.append(
                {
                    "hex": s[STATE_ICAO24],
                    "flight": s[STATE_CALLSIGN],
                    "lat": lat,
                    "lon": lon,
                    "alt_baro": round(baro_alt_m * METERS_TO_FEET) if baro_alt_m is not None else None,
                    "track": s[STATE_TRUE_TRACK] or 0.0,
                }
            )
        return aircraft
