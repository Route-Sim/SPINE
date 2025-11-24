"""Thread-safe simulation state management."""

import threading


class SimulationState:
    """Thread-safe simulation state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._paused = False
        self._tick_rate = 20.0  # ticks per second
        self._speed = 1.0  # simulation seconds per real second
        self._dt_s = 1.0 / 20.0  # seconds per tick (calculated as speed / tick_rate)
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

    @property
    def speed(self) -> float:
        """Simulation speed (simulation seconds per real second)."""
        with self._lock:
            return self._speed

    @property
    def dt_s(self) -> float:
        """Simulation speed (seconds per tick, calculated as speed / tick_rate)."""
        with self._lock:
            return self._dt_s

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
        """Set tick rate and recalculate dt_s based on current speed.

        Args:
            rate: Ticks per second, clamped between 0.1 and 100.0
        """
        with self._lock:
            self._tick_rate = max(0.1, min(100.0, rate))  # Clamp between 0.1 and 100 Hz
            # Recalculate dt_s based on current speed
            self._dt_s = self._speed / self._tick_rate

    def set_speed(self, speed: float) -> None:
        """Set simulation speed (simulation seconds per real second) and recalculate dt_s.

        Args:
            speed: Simulation seconds per real second, clamped between 0.01 and 10.0
        """
        with self._lock:
            self._speed = max(0.01, min(10.0, speed))
            # Recalculate dt_s based on current tick_rate
            self._dt_s = self._speed / self._tick_rate

    def increment_tick(self) -> None:
        with self._lock:
            self._current_tick += 1
