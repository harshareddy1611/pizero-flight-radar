import math
import time

import pygame

from . import geo

BG_COLOR = (2, 6, 12)
RING_COLOR_DIM = (0, 45, 40)
RING_COLOR_BRIGHT = (0, 150, 130)
TICK_COLOR = (0, 90, 80)
LABEL_COLOR = (110, 235, 210)
LABEL_BG_COLOR = (2, 14, 12)
PLANE_COLOR = (255, 200, 60)
PLANE_GLOW_COLOR = (110, 80, 15)
PLANE_OUTLINE_COLOR = (255, 240, 210)
TRAIL_COLOR = (140, 100, 20)
HOME_COLOR = (255, 70, 70)
HOME_RING_COLOR = (255, 220, 220)
SWEEP_COLOR = (60, 255, 190)

SWEEP_TAIL_STEPS = 10
SWEEP_TAIL_SPREAD_DEG = 26
SWEEP_PERIOD_S = 6.0

RANGE_PRESETS_KM = [15, 30, 60, 100, 150]
RING_RATIOS = (0.25, 0.5, 0.75, 1.0)


def _lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


class Renderer:
    def __init__(self, cfg):
        display_cfg = cfg["display"]
        radar_cfg = cfg["radar"]

        self.width = display_cfg["width"]
        self.height = display_cfg["height"]
        self.rotate_deg = display_cfg.get("rotate_degrees", 0)
        self.label_mode = "basic"  # "basic" (callsign/altitude) or "detail" (type/route)

        self.center_x = self.width // 2
        self.center_y = self.height // 2
        self.screen_radius_px = min(self.center_x, self.center_y) - 14

        configured_range = radar_cfg["max_range_km"]
        self._range_idx = min(
            range(len(RANGE_PRESETS_KM)),
            key=lambda i: abs(RANGE_PRESETS_KM[i] - configured_range),
        )
        self.max_range_km = RANGE_PRESETS_KM[self._range_idx]
        self.km_per_px = self.max_range_km / self.screen_radius_px
        self.range_rings = [round(self.max_range_km * r) for r in RING_RATIOS]

        # The SPI display's /dev/fb1 is a plain Linux framebuffer (RGB565), not a
        # DRM/KMS device - modern SDL2 dropped fbdev support, so we can't use
        # pygame.display for output here. Instead we draw onto an off-screen
        # surface in the same 16bpp RGB565 format and write its raw bytes
        # straight to the framebuffer device ourselves.
        surface_args = ((self.width, self.height), 0, 16, (0xF800, 0x07E0, 0x001F, 0))
        self.screen = pygame.Surface(*surface_args)
        pygame.font.init()
        self.font = pygame.font.SysFont("monospace", 11)
        self.font_bold = pygame.font.SysFont("monospace", 11, bold=True)
        self.fbdev = open(display_cfg["fbdev"], "wb")

        self.background = pygame.Surface(*surface_args)
        self._render_background()

    def _set_range_index(self, new_idx):
        self._range_idx = max(0, min(len(RANGE_PRESETS_KM) - 1, new_idx))
        self.max_range_km = RANGE_PRESETS_KM[self._range_idx]
        self.km_per_px = self.max_range_km / self.screen_radius_px
        self.range_rings = [round(self.max_range_km * r) for r in RING_RATIOS]
        self._render_background()

    def zoom_in(self):
        self._set_range_index(self._range_idx - 1)

    def zoom_out(self):
        self._set_range_index(self._range_idx + 1)

    def cycle_label_mode(self):
        self.label_mode = "detail" if self.label_mode == "basic" else "basic"

    def _to_screen(self, distance_km, bearing_deg):
        return geo.polar_to_screen(
            distance_km, bearing_deg, self.km_per_px, self.center_x, self.center_y, self.rotate_deg
        )

    def _blit_label(self, surface, text, pos, font, color):
        rendered = font.render(text, True, color)
        pad_rect = rendered.get_rect(topleft=pos).inflate(4, 2)
        surface.fill(LABEL_BG_COLOR, pad_rect)
        surface.blit(rendered, pos)

    def _render_background(self):
        self.background.fill(BG_COLOR)

        for ring_km in self.range_rings:
            r_px = int(ring_km / self.km_per_px)
            pygame.draw.circle(self.background, RING_COLOR_DIM, (self.center_x, self.center_y), r_px, 2)
            pygame.draw.circle(self.background, RING_COLOR_BRIGHT, (self.center_x, self.center_y), r_px, 1)
            self._blit_label(
                self.background, f"{ring_km}", (self.center_x + 4, self.center_y - r_px - 12),
                self.font, LABEL_COLOR,
            )

        # Cardinal ticks around the outer ring instead of a full crosshair - less
        # visual clutter, still reads as a compass.
        outer_r = self.screen_radius_px
        for angle_deg, label in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
            theta = math.radians(angle_deg + self.rotate_deg)
            x1 = self.center_x + (outer_r - 6) * math.sin(theta)
            y1 = self.center_y - (outer_r - 6) * math.cos(theta)
            x2 = self.center_x + (outer_r + 4) * math.sin(theta)
            y2 = self.center_y - (outer_r + 4) * math.cos(theta)
            pygame.draw.line(self.background, TICK_COLOR, (x1, y1), (x2, y2), 2)
            label_surf = self.font_bold.render(label, True, RING_COLOR_BRIGHT)
            label_rect = label_surf.get_rect(center=(x1 - (outer_r + 10) * 0.02, y1))
            self.background.blit(label_surf, label_rect)

        pygame.draw.circle(self.background, HOME_RING_COLOR, (self.center_x, self.center_y), 5, 1)
        pygame.draw.circle(self.background, HOME_COLOR, (self.center_x, self.center_y), 3)

    def _draw_sweep(self):
        t = time.monotonic()
        sweep_angle = (t % SWEEP_PERIOD_S) / SWEEP_PERIOD_S * 360.0

        for i in range(SWEEP_TAIL_STEPS, -1, -1):
            angle = sweep_angle - i * (SWEEP_TAIL_SPREAD_DEG / SWEEP_TAIL_STEPS)
            brightness = 1.0 - (i / SWEEP_TAIL_STEPS)
            color = _lerp_color(BG_COLOR, SWEEP_COLOR, brightness * brightness)
            theta = math.radians(angle + self.rotate_deg)
            x = self.center_x + self.screen_radius_px * math.sin(theta)
            y = self.center_y - self.screen_radius_px * math.cos(theta)
            pygame.draw.line(self.screen, color, (self.center_x, self.center_y), (x, y), 1)

    def _draw_aircraft(self, entry):
        if entry.distance_km > self.max_range_km:
            return

        trail_points = list(entry.trail)
        for i, (dist, brg) in enumerate(trail_points):
            x, y = self._to_screen(dist, brg)
            age_t = i / max(len(trail_points) - 1, 1)
            color = _lerp_color(BG_COLOR, TRAIL_COLOR, 0.25 + 0.6 * age_t)
            radius = 1 if age_t < 0.6 else 2
            pygame.draw.circle(self.screen, color, (int(x), int(y)), radius)

        x, y = self._to_screen(entry.distance_km, entry.bearing_deg)
        heading_rad = math.radians(entry.track + self.rotate_deg)

        def point(dist_forward, dist_side, angle_offset=0.0):
            a = heading_rad + angle_offset
            return (x + dist_forward * math.sin(a) - dist_side * math.cos(a),
                    y - dist_forward * math.cos(a) - dist_side * math.sin(a))

        # Soft glow behind the marker: a wider, dim triangle drawn first.
        glow_shape = [point(9, 0), point(-5, 5), point(-5, -5)]
        pygame.draw.polygon(self.screen, PLANE_GLOW_COLOR, glow_shape)

        core_shape = [point(7, 0), point(-4, 4), point(-4, -4)]
        pygame.draw.polygon(self.screen, PLANE_COLOR, core_shape)
        pygame.draw.polygon(self.screen, PLANE_OUTLINE_COLOR, core_shape, 1)

        line1 = []
        line2 = []
        if self.label_mode == "basic":
            if entry.flight:
                line1.append(entry.flight.strip())
            if entry.alt_baro is not None:
                line2.append(f"FL{entry.alt_baro // 100}")
        else:
            line1.append(entry.aircraft_type or (entry.flight or "").strip())
            if entry.route:
                line2.append(entry.route.replace("-", ">"))
            line1 = [p for p in line1 if p]

        label_y = y - 6
        if line1:
            self._blit_label(self.screen, " ".join(line1), (x + 8, label_y), self.font, LABEL_COLOR)
            label_y += 12
        if line2:
            self._blit_label(self.screen, " ".join(line2), (x + 8, label_y), self.font, LABEL_COLOR)

    def draw(self, aircraft_list):
        self.screen.blit(self.background, (0, 0))
        self._draw_sweep()
        for entry in aircraft_list:
            self._draw_aircraft(entry)
        self.fbdev.seek(0)
        self.fbdev.write(self.screen.get_buffer().raw)
        self.fbdev.flush()
