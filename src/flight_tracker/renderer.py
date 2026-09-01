import math

import pygame

from . import geo

BG_COLOR = (5, 10, 5)
RING_COLOR = (0, 60, 0)
LABEL_COLOR = (0, 200, 0)
PLANE_COLOR = (0, 255, 60)
TRAIL_COLOR = (0, 100, 30)
HOME_COLOR = (255, 60, 60)


class Renderer:
    def __init__(self, cfg):
        display_cfg = cfg["display"]
        radar_cfg = cfg["radar"]

        self.width = display_cfg["width"]
        self.height = display_cfg["height"]
        self.rotate_deg = display_cfg.get("rotate_degrees", 0)
        self.max_range_km = radar_cfg["max_range_km"]
        self.range_rings = radar_cfg["range_rings"]
        self.show_callsign = radar_cfg["show_callsign"]
        self.show_altitude = radar_cfg["show_altitude"]

        self.center_x = self.width // 2
        self.center_y = self.height // 2
        self.screen_radius_px = min(self.center_x, self.center_y) - 20
        self.km_per_px = self.max_range_km / self.screen_radius_px

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.font.init()
        self.font = pygame.font.SysFont("monospace", 11)

    def _to_screen(self, distance_km, bearing_deg):
        return geo.polar_to_screen(
            distance_km, bearing_deg, self.km_per_px, self.center_x, self.center_y, self.rotate_deg
        )

    def _draw_rings(self):
        for ring_km in self.range_rings:
            r_px = int(ring_km / self.km_per_px)
            pygame.draw.circle(self.screen, RING_COLOR, (self.center_x, self.center_y), r_px, 1)
            label = self.font.render(f"{ring_km}km", True, RING_COLOR)
            self.screen.blit(label, (self.center_x + 4, self.center_y - r_px - 12))

        pygame.draw.line(self.screen, RING_COLOR, (self.center_x, 0), (self.center_x, self.height), 1)
        pygame.draw.line(self.screen, RING_COLOR, (0, self.center_y), (self.width, self.center_y), 1)
        pygame.draw.circle(self.screen, HOME_COLOR, (self.center_x, self.center_y), 3)

    def _draw_aircraft(self, entry):
        if entry.distance_km > self.max_range_km:
            return

        for dist, brg in entry.trail:
            x, y = self._to_screen(dist, brg)
            pygame.draw.circle(self.screen, TRAIL_COLOR, (int(x), int(y)), 1)

        x, y = self._to_screen(entry.distance_km, entry.bearing_deg)
        heading_rad = math.radians(entry.track + self.rotate_deg)
        tip = (x + 6 * math.sin(heading_rad), y - 6 * math.cos(heading_rad))
        left = (x + 4 * math.sin(heading_rad + 2.5), y - 4 * math.cos(heading_rad + 2.5))
        right = (x + 4 * math.sin(heading_rad - 2.5), y - 4 * math.cos(heading_rad - 2.5))
        pygame.draw.polygon(self.screen, PLANE_COLOR, [tip, left, right])

        label_parts = []
        if self.show_callsign and entry.flight:
            label_parts.append(entry.flight)
        if self.show_altitude and entry.alt_baro is not None:
            label_parts.append(f"{entry.alt_baro}ft")
        if label_parts:
            label = self.font.render(" ".join(label_parts), True, LABEL_COLOR)
            self.screen.blit(label, (x + 6, y - 6))

    def draw(self, aircraft_list):
        self.screen.fill(BG_COLOR)
        self._draw_rings()
        for entry in aircraft_list:
            self._draw_aircraft(entry)
        pygame.display.flip()
