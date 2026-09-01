import queue
import threading
import time

import gpiod
from gpiod.line import Bias, Direction, Value

# Argon POD 2.8" button GPIO pins (BCM numbering), from Argon's own
# argonpodd.py reference daemon. Board has an external pull-up on each line:
# idle reads ACTIVE, a press pulls it to INACTIVE.
BUTTON_PINS = {
    "A": 16,
    "B": 20,
    "C": 21,
    "D": 26,
}

POLL_INTERVAL_S = 0.03


class ButtonWatcher:
    """Polls the Argon POD's 4 buttons in a background thread and queues press events."""

    def __init__(self):
        self._request = gpiod.request_lines(
            "/dev/gpiochip0",
            consumer="flight-tracker-buttons",
            config={
                pin: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)
                for pin in BUTTON_PINS.values()
            },
        )
        self._events = queue.Queue()
        self._prev_values = {name: Value.ACTIVE for name in BUTTON_PINS}
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        while True:
            for name, pin in BUTTON_PINS.items():
                value = self._request.get_value(pin)
                if value != self._prev_values[name] and value == Value.INACTIVE:
                    self._events.put(name)
                self._prev_values[name] = value
            time.sleep(POLL_INTERVAL_S)

    def poll_events(self):
        """Return button names pressed since the last call, draining the queue."""
        pressed = []
        while True:
            try:
                pressed.append(self._events.get_nowait())
            except queue.Empty:
                break
        return pressed
