"""GPU telemetry for the NVIDIA GB10 (Grace Blackwell).

GB10 has coherent unified memory rather than discrete VRAM, so several
nvidia-smi fields that work everywhere else return N/A here. Measured on the
target machine:

    WORKS   utilization.gpu, power.draw, temperature.gpu, clocks.sm
    N/A     memory.total, memory.used, memory.free, clocks.mem, fan.speed
    TRAP    `nvidia-smi dmon` / `pmon` report memory as 0 rather than N/A,
            which is silently wrong -- do not use them.

Per-process memory DOES work via --query-compute-apps, and the unified pool
size comes from /proc/meminfo. Falls back to a degraded reading rather than
raising, so a demo dashboard never crashes on a telemetry hiccup.
"""
from __future__ import annotations

import shutil
import subprocess

GPU_FIELDS = ("utilization.gpu", "power.draw", "temperature.gpu", "clocks.sm")


def _run(args: list[str], timeout: float = 2.0) -> str | None:
    if shutil.which(args[0]) is None:
        return None
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (subprocess.SubprocessError, OSError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _to_float(text: str) -> float | None:
    text = text.strip()
    if not text or text.startswith("[N/A]") or text == "N/A":
        return None
    try:
        return float(text.split()[0])
    except ValueError:
        return None


def read_unified_memory() -> dict:
    """Total/available system memory, which on GB10 is also the GPU's pool."""
    info: dict[str, float] = {}
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                parts = rest.split()
                if parts:
                    info[key] = float(parts[0]) / (1024 * 1024)   # kB -> GiB
    except OSError:
        return {}
    return {
        "unified_total_gib": round(info.get("MemTotal", 0.0), 1),
        "unified_available_gib": round(info.get("MemAvailable", 0.0), 1),
    }


def read_processes() -> list[dict]:
    """Per-process GPU memory. This DOES work on GB10, unlike memory.total."""
    raw = _run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                "--format=csv,noheader,nounits"])
    if not raw:
        return []
    procs = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        procs.append({
            "pid": parts[0],
            "name": parts[1].split("/")[-1],
            "memory_mib": _to_float(parts[2]),
        })
    return procs


def read_gpu() -> dict:
    """One telemetry sample, safe to poll a few times a second."""
    raw = _run(["nvidia-smi", f"--query-gpu=name,{','.join(GPU_FIELDS)}",
                "--format=csv,noheader,nounits"])
    if not raw:
        return {"available": False,
                "reason": "nvidia-smi not present or returned an error",
                **read_unified_memory()}

    parts = [p.strip() for p in raw.splitlines()[0].split(",")]
    name = parts[0] if parts else "unknown"
    values = [_to_float(p) for p in parts[1:]]
    sample = dict(zip(GPU_FIELDS, values))

    procs = read_processes()
    return {
        "available": True,
        "name": name,
        "utilization_pct": sample.get("utilization.gpu"),
        "power_watts": sample.get("power.draw"),
        "temperature_c": sample.get("temperature.gpu"),
        "sm_clock_mhz": sample.get("clocks.sm"),
        "processes": procs,
        "process_memory_mib": sum(p["memory_mib"] or 0 for p in procs) or None,
        **read_unified_memory(),
        "note": ("GB10 shares coherent system memory with the CPU, so total/free "
                 "VRAM is not reported by nvidia-smi; per-process memory is."),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(read_gpu(), indent=2))
