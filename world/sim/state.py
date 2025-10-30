"""Thread-safe simulation state management."""

import threading


class SimulationState:
    """Thread-safe simulation state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._paused = False
        self._tick_rate = 20.0  # ticks per second
        self._current_tick = 0

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    @property
    def tick_rate(self) -> float:
        with self._lock:
            return self._tick_rate

    @property
    def current_tick(self) -> int:
        with self._lock:
            return self._current_tick

    def start(self) -> None:
        with self._lock:
            self._running = True
            self._paused = False

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._paused = False

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    def set_tick_rate(self, rate: float) -> None:
        with self._lock:
            self._tick_rate = max(0.1, min(100.0, rate))  # Clamp between 0.1 and 100 Hz

    def increment_tick(self) -> None:
        with self._lock:
            self._current_tick += 1
