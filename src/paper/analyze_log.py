#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ====== DEFAULTS (TU LOG) ======
DEFAULT_BASENAME = "research_log_1772250781.json"
DEFAULT_LOG_DIR = Path("data/logs")
DEFAULT_OUT_DIR = Path("data/logs")


def safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def percentile(arr: np.ndarray, p: float) -> float:
    if arr.size == 0:
        return float("nan")
    return float(np.percentile(arr, p))


def fmt(x: float, nd: int = 3) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "N/A"
    return f"{x:.{nd}f}"


def resolve_log_path(name_or_path: str) -> Path:
    """
    Accepts:
      - full/relative path, or
      - basename like 'research_log_1772250781' (tries .json then .log in data/logs)
    """
    p = Path(name_or_path)
    if p.exists():
        return p

    # try in default dir
    cand_json = DEFAULT_LOG_DIR / f"{name_or_path}.json"
    if cand_json.exists():
        return cand_json

    cand_log = DEFAULT_LOG_DIR / f"{name_or_path}.log"
    if cand_log.exists():
        return cand_log

    # also allow passing already-prefixed basename without extension
    # e.g. 'research_log_1772250781' (handled above), but keep this for clarity
    cand_json2 = DEFAULT_LOG_DIR / f"{name_or_path}"
    if cand_json2.exists():
        return cand_json2

    raise FileNotFoundError(
        f"No encuentro el log: '{name_or_path}'. Probé:\n"
        f"  - {p}\n  - {cand_json}\n  - {cand_log}\n  - {cand_json2}"
    )


def load_json_log(path: Path) -> List[Dict[str, Any]]:
    """
    Loads either:
    - a standard JSON array, or
    - JSON lines (one object per line) as fallback.
    """
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        raise ValueError("Archivo vacío")

    # Standard JSON array
    if text[0] == "[":
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("Se esperaba un JSON array en la raíz.")
        return data

    # Fallback: JSON Lines
    rows: List[Dict[str, Any]] = []
    for ln in text.splitlines():
        ln = ln.strip().rstrip(",")
        if not ln:
            continue
        obj = json.loads(ln)
        if isinstance(obj, dict):
            rows.append(obj)
        else:
            raise ValueError("Modo JSONL espera 1 objeto JSON por línea.")
    return rows


@dataclass
class ThroughputStats:
    n: int
    t_start: float
    t_end: float
    session_s: float
    dt_med_ms: float
    dt_p95_ms: float
    dt_mean_ms: float
    dt_min_ms: float
    feff_hz: float
    fps_mean: float
    fps_min: float
    fps_p05: float


@dataclass
class RobustnessStats:
    hand_drop_rate: float
    finger_presence: Dict[str, float]
    stereo_fail_rate: Optional[float]
    fallback_rate: Optional[float]


@dataclass
class MusicalStats:
    note_on: int
    note_off: int
    stuck_notes_end: int
    bounce_count: int
    bounce_rate: float
    events_per_s: float
    dur_med_s: Optional[float]
    dur_p05_s: Optional[float]
    dur_p95_s: Optional[float]


def analyze_throughput(rows: List[Dict[str, Any]]) -> ThroughputStats:
    t = [safe_float(r.get("t")) for r in rows]
    t = [x for x in t if x is not None]
    if len(t) < 2:
        raise ValueError("No hay suficientes muestras válidas de 't' (>=2).")

    t = np.array(t, dtype=float)
    t.sort()

    dt = np.diff(t)  # seconds
    dt = dt[dt > 0]  # filter non-positive deltas
    if dt.size == 0:
        raise ValueError("Todos los Δt son no-positivos; revisa timestamps.")

    session_s = float(t[-1] - t[0])

    dt_med = float(np.median(dt))
    dt_p95 = percentile(dt, 95)
    dt_mean = float(np.mean(dt))
    dt_min = float(np.min(dt))

    feff = 1.0 / dt_med

    fps_inst = 1.0 / dt
    fps_mean = float(np.mean(fps_inst))
    fps_min = float(np.min(fps_inst))
    fps_p05 = percentile(fps_inst, 5)  # worst 5%

    return ThroughputStats(
        n=int(len(t)),
        t_start=float(t[0]),
        t_end=float(t[-1]),
        session_s=session_s,
        dt_med_ms=dt_med * 1000.0,
        dt_p95_ms=dt_p95 * 1000.0,
        dt_mean_ms=dt_mean * 1000.0,
        dt_min_ms=dt_min * 1000.0,
        feff_hz=feff,
        fps_mean=fps_mean,
        fps_min=fps_min,
        fps_p05=fps_p05,
    )


def analyze_robustness(rows: List[Dict[str, Any]]) -> RobustnessStats:
    total_frames = 0
    empty_frames = 0
    finger_counts: Dict[str, int] = {}

    stereo_fail_count = 0
    fallback_count = 0
    stereo_flag_seen = False
    fallback_flag_seen = False

    for r in rows:
        total_frames += 1
        fingers = r.get("fingers", {})
        if not isinstance(fingers, dict):
            fingers = {}

        if len(fingers) == 0:
            empty_frames += 1
        else:
            for fname in fingers.keys():
                finger_counts[fname] = finger_counts.get(fname, 0) + 1

        # Optional flags (solo si existen en tu log)
        if "stereo_ok" in r:
            stereo_flag_seen = True
            stereo_ok = bool(r.get("stereo_ok"))
            if not stereo_ok:
                stereo_fail_count += 1
        if "fallback_used" in r:
            fallback_flag_seen = True
            if bool(r.get("fallback_used")):
                fallback_count += 1

    hand_drop_rate = empty_frames / total_frames if total_frames else float("nan")
    finger_presence = {k: v / total_frames for k, v in sorted(finger_counts.items(), key=lambda x: -x[1])}

    stereo_fail_rate = (stereo_fail_count / total_frames) if stereo_flag_seen else None
    fallback_rate = (fallback_count / total_frames) if fallback_flag_seen else None

    return RobustnessStats(
        hand_drop_rate=hand_drop_rate,
        finger_presence=finger_presence,
        stereo_fail_rate=stereo_fail_rate,
        fallback_rate=fallback_rate,
    )


def analyze_musical(rows: List[Dict[str, Any]], bounce_window_s: float = 0.150) -> MusicalStats:
    cleaned: List[Tuple[float, List[int]]] = []
    for r in rows:
        ti = safe_float(r.get("t"))
        if ti is None:
            continue
        notes = r.get("global_notes", [])
        if notes is None or not isinstance(notes, list):
            notes = []
        nn: List[int] = []
        for x in notes:
            try:
                nn.append(int(x))
            except Exception:
                pass
        cleaned.append((ti, nn))

    if len(cleaned) < 2:
        raise ValueError("No hay suficientes muestras para analizar musicalidad.")

    cleaned.sort(key=lambda x: x[0])

    prev: set[int] = set()
    note_on = 0
    note_off = 0

    last_on_time: Dict[int, float] = {}
    bounce_count = 0

    active_since: Dict[int, float] = {}
    durations: List[float] = []

    t_start = cleaned[0][0]
    t_end = cleaned[-1][0]
    session_s = max(1e-9, (t_end - t_start))

    for ti, notes_list in cleaned:
        curr = set(notes_list)
        ons = curr - prev
        offs = prev - curr

        for n in ons:
            note_on += 1
            if n in last_on_time and (ti - last_on_time[n]) < bounce_window_s:
                bounce_count += 1
            last_on_time[n] = ti
            active_since[n] = ti

        for n in offs:
            note_off += 1
            if n in active_since:
                durations.append(ti - active_since[n])
                del active_since[n]

        prev = curr

    stuck_notes_end = len(prev)

    dur_med = dur_p05 = dur_p95 = None
    if durations:
        d = np.array(durations, dtype=float)
        dur_med = float(np.median(d))
        dur_p05 = float(np.percentile(d, 5))
        dur_p95 = float(np.percentile(d, 95))

    bounce_rate = (bounce_count / note_on) if note_on > 0 else float("nan")
    events_per_s = note_on / session_s

    return MusicalStats(
        note_on=note_on,
        note_off=note_off,
        stuck_notes_end=stuck_notes_end,
        bounce_count=bounce_count,
        bounce_rate=bounce_rate,
        events_per_s=events_per_s,
        dur_med_s=dur_med,
        dur_p05_s=dur_p05,
        dur_p95_s=dur_p95,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--log",
        type=str,
        default=DEFAULT_BASENAME,
        help=f"Ruta o basename del log (default: {DEFAULT_BASENAME} en {DEFAULT_LOG_DIR})",
    )
    ap.add_argument("--bounce_ms", type=float, default=150.0, help="Ventana de rebote en ms (default 150)")
    ap.add_argument(
        "--out",
        type=str,
        default="",
        help="Ruta de salida para summary.json (si vacío, se guarda en data/logs/summary_<basename>.json)",
    )
    args = ap.parse_args()

    log_path = resolve_log_path(args.log)
    rows = load_json_log(log_path)

    thr = analyze_throughput(rows)
    rob = analyze_robustness(rows)
    mus = analyze_musical(rows, bounce_window_s=args.bounce_ms / 1000.0)

    # basename real para salida
    base = log_path.stem  # si es .json o .log, stem funciona

    summary = {
        "log_path": str(log_path),
        "C1_throughput": {
            "N": thr.n,
            "t_start_s": thr.t_start,
            "t_end_s": thr.t_end,
            "session_s": thr.session_s,
            "dt_med_ms": thr.dt_med_ms,
            "dt_p95_ms": thr.dt_p95_ms,
            "dt_mean_ms": thr.dt_mean_ms,
            "dt_min_ms": thr.dt_min_ms,
            "f_eff_hz": thr.feff_hz,
            "fps_mean": thr.fps_mean,
            "fps_min": thr.fps_min,
            "fps_p05": thr.fps_p05,
        },
        "C2_robustness": {
            "hand_drop_rate": rob.hand_drop_rate,
            "finger_presence_rate": rob.finger_presence,
            "stereo_fail_rate": rob.stereo_fail_rate,   # None si no existe en el log
            "fallback_rate": rob.fallback_rate,         # None si no existe en el log
        },
        "C3_musical": {
            "NOTEON": mus.note_on,
            "NOTEOFF": mus.note_off,
            "stuck_notes_end": mus.stuck_notes_end,
            "bounce_count": mus.bounce_count,
            "bounce_rate": mus.bounce_rate,
            "events_per_s": mus.events_per_s,
            "duration_med_s": mus.dur_med_s,
            "duration_p05_s": mus.dur_p05_s,
            "duration_p95_s": mus.dur_p95_s,
        },
    }

    print("\n=== C1 Rendimiento (Throughput/Latencia) ===")
    print(f"log                : {log_path}")
    print(f"N muestras          : {thr.n}")
    print(f"Duración sesión (s) : {fmt(thr.session_s, 3)}")
    print(f"Δt_med (ms)         : {fmt(thr.dt_med_ms, 2)}")
    print(f"Δt_p95 (ms)         : {fmt(thr.dt_p95_ms, 2)}")
    print(f"f_eff (Hz)          : {fmt(thr.feff_hz, 2)}")
    print(f"FPS_mean            : {fmt(thr.fps_mean, 2)}")
    print(f"FPS_min             : {fmt(thr.fps_min, 2)}")
    print(f"FPS_p05 (peor 5%)    : {fmt(thr.fps_p05, 2)}")

    print("\n=== C2 Robustez (según lo que existe en el log) ===")
    print(f"hand_drop_rate (fingers vacío): {fmt(rob.hand_drop_rate * 100, 2)} %")
    if rob.stereo_fail_rate is None:
        print("stereo_fail_rate    : N/A (no existe 'stereo_ok' en el log)")
    else:
        print(f"stereo_fail_rate    : {fmt(rob.stereo_fail_rate * 100, 2)} %")
    if rob.fallback_rate is None:
        print("fallback_rate       : N/A (no existe 'fallback_used' en el log)")
    else:
        print(f"fallback_rate       : {fmt(rob.fallback_rate * 100, 2)} %")

    print("\n=== C3 Estabilidad musical (global_notes) ===")
    print(f"NOTEON / NOTEOFF    : {mus.note_on} / {mus.note_off}")
    print(f"stuck_notes_end     : {mus.stuck_notes_end}")
    print(f"bounces (<{args.bounce_ms:.0f}ms)  : {mus.bounce_count}  (rate={fmt(mus.bounce_rate*100,2)} %)")
    print(f"eventos/s (NOTEON)  : {fmt(mus.events_per_s, 3)}")
    if mus.dur_med_s is not None:
        print(f"duración mediana    : {fmt(mus.dur_med_s, 4)} s")
        print(f"duración p05/p95    : {fmt(mus.dur_p05_s,4)} / {fmt(mus.dur_p95_s,4)} s")
    else:
        print("duración de nota    : N/A (no hubo NOTE-OFF suficientes)")

    out_path: Path
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = DEFAULT_OUT_DIR / f"summary_{base}.json"

    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[OK] Summary guardado en: {out_path}")


if __name__ == "__main__":
    main()