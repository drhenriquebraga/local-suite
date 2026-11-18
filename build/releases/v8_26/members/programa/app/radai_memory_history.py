"""Fixed-schema workstation memory samples while Run now or the Watcher owns a case."""
import ctypes
from functools import wraps
import json
import os
from pathlib import Path
import tempfile
import threading
import time


_PHASES = ("pipeline", "inference", "postprocess", "write_full", "write_study", "write_other")
_LOW = ("available_min_mib", "commit_free_min_mib")
_HIGH = ("private_max_mib", "working_set_max_mib", "physical_total_mib", "commit_limit_mib")
_CONTEXT = threading.local()
_INTERVAL = 2
_FLUSH_SECONDS = 16


class _Performance(ctypes.Structure):
    _fields_ = ([("cb", ctypes.c_uint32)] +
                [(name, ctypes.c_size_t) for name in (
                    "CommitTotal", "CommitLimit", "CommitPeak", "PhysicalTotal", "PhysicalAvailable",
                    "SystemCache", "KernelTotal", "KernelPaged", "KernelNonpaged", "PageSize")] +
                [(name, ctypes.c_uint32) for name in ("HandleCount", "ProcessCount", "ThreadCount")])


class _Process(ctypes.Structure):
    _fields_ = ([("cb", ctypes.c_uint32), ("faults", ctypes.c_uint32)] +
                [(name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")])


def _sample():
    psapi = ctypes.windll.psapi
    system = _Performance()
    process = _Process()
    system.cb, process.cb = ctypes.sizeof(system), ctypes.sizeof(process)
    mib = 1024 ** 2
    sample = {}
    if psapi.GetPerformanceInfo(ctypes.byref(system), system.cb):
        sample.update(available_min_mib=system.PhysicalAvailable * system.PageSize // mib,
                      commit_free_min_mib=max(0, system.CommitLimit - system.CommitTotal) * system.PageSize // mib,
                      physical_total_mib=system.PhysicalTotal * system.PageSize // mib,
                      commit_limit_mib=system.CommitLimit * system.PageSize // mib)
    if psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(process), process.cb):
        sample.update(private_max_mib=process.PrivateUsage // mib, working_set_max_mib=process.WorkingSetSize // mib)
    return sample


def _merge(dest, values):
    for phase in _PHASES:
        source = values.get(phase)
        if not isinstance(source, dict) or type(source.get("samples")) is not int or source["samples"] <= 0:
            continue
        row = dest.setdefault(phase, {"samples": 0})
        row["samples"] = min(2**31 - 1, row["samples"] + source["samples"])
        for key in _LOW + _HIGH:
            value = source.get(key)
            if type(value) is int and 0 <= value < 2**31:
                combine = min if key in _LOW else max
                row[key] = combine(row.get(key, value), value)


def _persist(target, pending):
    import msvcrt

    with target.with_suffix(".lock").open("a+b") as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        temp = None
        try:
            previous = {}
            if target.exists() and target.stat().st_size <= 16384:
                try:
                    record = json.loads(target.read_bytes())
                    if isinstance(record, dict) and record.get("schema") == 1 and isinstance(record.get("phases"), dict):
                        _merge(previous, record["phases"])
                except (ValueError, UnicodeError):
                    pass
            _merge(previous, pending)
            with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=target.parent,
                                             prefix=".memoria-", suffix=".tmp", delete=False) as f:
                temp = Path(f.name)
                json.dump({"schema": 1, "phases": previous}, f, separators=(",", ":"))
            os.replace(temp, target)
        finally:
            if temp:
                temp.unlink(missing_ok=True)
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


class _Monitor:
    def __init__(self, target):
        self.target = target
        self.stopped = threading.Event()
        self.lock = threading.Lock()
        self.stack = []
        self.pending = {}
        self.next_save = time.monotonic() + _FLUSH_SECONDS
        self.thread = threading.Thread(target=self._run, daemon=True, name="local-suite-memory")

    def _capture(self):
        try:
            sample = _sample()
            if sample:
                for phase in set(self.stack):
                    _merge(self.pending, {phase: dict(sample, samples=1)})
        except (OSError, AttributeError, MemoryError):
            pass

    def _save(self):
        if not self.pending:
            return
        try:
            _persist(self.target, self.pending)
            self.pending.clear()
        except (OSError, ValueError, MemoryError):
            pass

    def _run(self):
        while not self.stopped.wait(_INTERVAL):
            with self.lock:
                self._capture()
                if time.monotonic() >= self.next_save:
                    self._save()
                    self.next_save = time.monotonic() + _FLUSH_SECONDS

    def enter(self, name):
        with self.lock:
            self.stack.append(name)
            self._capture()

    def leave(self):
        with self.lock:
            self._capture()
            self.stack.pop()

    def close(self):
        self.stopped.set()
        with self.lock:
            self._save()


def _target():
    here = Path(__file__).resolve().parent
    if os.name != "nt" or not (here / "entrega.txt").is_file():
        return None
    folder = here / "calibracao"
    if folder.is_dir():
        return folder / "memoria-motor-v1.json"
    folder.mkdir(exist_ok=True)
    return folder / "memoria-motor-v1.json"


def phase(name):
    if name not in _PHASES:
        raise ValueError("unknown memory phase")

    def decorate(func):
        @wraps(func)
        def monitored(*args, **kwargs):
            monitor = getattr(_CONTEXT, "monitor", None)
            owner = monitor is None and name == "pipeline"
            if owner:
                try:
                    target = _target()
                    if target is not None:
                        monitor = _Monitor(target)
                        monitor.thread.start()
                        _CONTEXT.monitor = monitor
                except (OSError, RuntimeError, MemoryError):
                    monitor = None
            if monitor is None:
                return func(*args, **kwargs)
            monitor.enter(name)
            try:
                return func(*args, **kwargs)
            finally:
                monitor.leave()
                if owner:
                    _CONTEXT.monitor = None
                    monitor.close()
        return monitored
    return decorate

