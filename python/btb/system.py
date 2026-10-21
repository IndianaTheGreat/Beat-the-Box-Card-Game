"""
==============================================
CPU AND MEMORY SCAN FOR PARALLEL RUNS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/system.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-21
Last Tested: 2026-10-21 (pytest: 342 passed)

VERSION 1.1 CHANGES (2026-10-21):
- resolve_workers never gives more than 61 helpers on Windows
  (WINDOWS_POOL_LIMIT): a process pool there refuses more, so a PC with
  over 61 cores crashed the run instead of using 61.

VERSION 1.0 CHANGES (2026-10-20):
- New. Decides how many helper processes the Simulator and Optimizer may
  use, so a big run never takes over the computer.

DESCRIPTION:
-----------
Before a parallel run, scan() measures how busy the CPU is (over a fifth
of a second) and how much memory is free. auto_workers() then picks a
safe number of helper processes:

  * never more than 75% of the cores,
  * always one core left free for you and the window,
  * only cores that are actually idle right now,
  * about 150 MB of free memory per helper.

Helpers also run at low priority (lower_priority), so anything you are
doing on the computer comes first. No GUI code; standard library only.

DEPENDENCIES:
------------
- Standard library: os, sys, time, ctypes (Windows only), dataclasses

KEY FUNCTIONS:
-------------
- cpu_count() -> cores this process may use
- cpu_idle_fraction(sample_s) -> 0.0-1.0 or None if unknown
- free_memory_mb() -> int or None if unknown
- auto_workers(cpus, idle, free_mb) -> safe helper count (pure function)
- scan() -> ResourceScan(cpus, idle, free_mb, workers)
- resolve_workers(setting) -> "auto" or a number -> helper count
- lower_priority() -> called in each helper process when it starts

ERROR HANDLING:
--------------
Every measurement is best effort. If the system can't be read, that
measurement is treated as unknown and the safe limits above still apply.

NOTES:
-----
- Windows: GetSystemTimes / GlobalMemoryStatusEx through ctypes.
- Linux: /proc/stat and /proc/meminfo. macOS: load average only.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Union

MAX_SHARE = 0.75          # never use more than this share of the cores
MB_PER_WORKER = 150       # memory budget per helper process
AUTO = "auto"


def cpu_count() -> int:
    """Cores this process is allowed to use."""
    counter = getattr(os, "process_cpu_count", None)  # Python 3.13+
    if counter:
        n = counter()
        if n:
            return n
    if hasattr(os, "sched_getaffinity"):
        try:
            return max(1, len(os.sched_getaffinity(0)))
        except OSError:
            pass
    return os.cpu_count() or 1


def _cpu_times() -> Optional[Tuple[float, float]]:
    """(idle, total) CPU time counters, or None when unavailable."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            idle, kernel, user = (wintypes.FILETIME(), wintypes.FILETIME(),
                                  wintypes.FILETIME())
            if not ctypes.windll.kernel32.GetSystemTimes(
                    ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                return None

            def value(ft) -> int:
                return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

            # Kernel time includes idle time on Windows.
            return float(value(idle)), float(value(kernel) + value(user))
        except Exception:
            return None
    try:
        with open("/proc/stat", encoding="ascii") as f:
            fields = [float(x) for x in f.readline().split()[1:]]
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0.0)  # idle + iowait
        return idle, sum(fields[:8])
    except (OSError, ValueError, IndexError):
        return None


def cpu_idle_fraction(sample_s: float = 0.2) -> Optional[float]:
    """Share of the CPU that is idle right now (0.0-1.0), or None."""
    first = _cpu_times()
    if first is not None:
        time.sleep(sample_s)
        second = _cpu_times()
        if second is not None:
            idle = second[0] - first[0]
            total = second[1] - first[1]
            if total > 0:
                return max(0.0, min(1.0, idle / total))
    if hasattr(os, "getloadavg"):  # macOS and other Unix
        try:
            load = os.getloadavg()[0]
            return max(0.0, min(1.0, 1.0 - load / cpu_count()))
        except OSError:
            pass
    return None


def free_memory_mb() -> Optional[int]:
    """Memory available to new programs, in MB, or None."""
    if sys.platform == "win32":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullAvailPhys // (1024 * 1024))
        except Exception:
            return None
        return None
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def auto_workers(cpus: int, idle: Optional[float] = None,
                 free_mb: Optional[int] = None) -> int:
    """A safe number of helper processes. Always at least 1.

    1 means "run in this process" (no helpers at all).
    """
    cpus = max(1, int(cpus))
    n = min(int(cpus * MAX_SHARE), cpus - 1)      # cap, and keep one core free
    if idle is not None:
        n = min(n, int(idle * cpus) - 1)          # only cores idle now, minus one
    if free_mb is not None:
        n = min(n, int(free_mb) // MB_PER_WORKER)
    return max(1, n)


@dataclass(frozen=True)
class ResourceScan:
    cpus: int
    idle: Optional[float]
    free_mb: Optional[int]
    workers: int

    def describe(self) -> str:
        idle = "unknown" if self.idle is None else f"{self.idle * 100:.0f}% idle"
        mem = "unknown" if self.free_mb is None else f"{self.free_mb:,} MB free"
        return (f"{self.cpus} cores ({idle}), {mem}: Auto uses "
                f"{self.workers} {'process' if self.workers == 1 else 'processes'}")


def scan(sample_s: float = 0.2) -> ResourceScan:
    cpus = cpu_count()
    idle = cpu_idle_fraction(sample_s)
    free = free_memory_mb()
    return ResourceScan(cpus, idle, free, auto_workers(cpus, idle, free))


# Windows can't wait on more than 61 helper processes at once, so a process
# pool there refuses more (Python raises ValueError).
WINDOWS_POOL_LIMIT = 61


def _pool_limit(n: int) -> int:
    return min(n, WINDOWS_POOL_LIMIT) if sys.platform == "win32" else n


def resolve_workers(setting: Union[str, int, None]) -> int:
    """'auto' (or None) -> scan(); a number -> clamped to 1..cores. Never
    more than WINDOWS_POOL_LIMIT on Windows."""
    if setting is None or str(setting).lower() == AUTO:
        return _pool_limit(scan().workers)
    try:
        n = int(setting)
    except (TypeError, ValueError):
        return _pool_limit(scan().workers)
    return _pool_limit(max(1, min(n, cpu_count())))


def lower_priority() -> None:
    """Run this process below normal priority (called in each helper)."""
    try:
        if sys.platform == "win32":
            import ctypes
            below_normal = 0x00004000
            kernel32 = ctypes.windll.kernel32
            kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), below_normal)
        else:
            os.nice(10)
    except Exception:
        pass  # best effort: a helper at normal priority still works