# analyze_research_log.py
import json
import re
import sys
from collections import defaultdict
import numpy as np

def pct(x, p):
    return float(np.percentile(x, p)) if len(x) else float("nan")

def load_data(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
    # A veces el JSON está envuelto en dict con una lista adentro
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    if isinstance(data, list):
        return data
    raise ValueError("Formato JSON no reconocido (no es lista ni dict con lista).")

def main():
    if len(sys.argv) < 2:
        print("Uso: python fps.py logs\\research_log_1772250781.json")
        sys.exit(1)

    path = sys.argv[1]
    data = load_data(path)

    # --- tiempos
    t = np.array([d.get("t") for d in data if isinstance(d, dict) and "t" in d], dtype=float)
    dt = np.diff(t) if len(t) > 1 else np.array([])

    print("=== Sampling / performance from t ===")
    if len(dt):
        print("samples:", int(len(t)))
        print("median_dt(s):", float(np.median(dt)))
        print("p95_dt(s):", pct(dt, 95))
        print("approx_Hz:", float(1.0 / np.median(dt)))
    else:
        print("No hay suficientes muestras para calcular dt/Hz.")

    # --- hover/touch z por dedo
    z_hover = defaultdict(list)
    z_touch = defaultdict(list)

    # --- global notes para eventos
    time_seq = []
    global_notes_seq = []

    for d in data:
        if not isinstance(d, dict):
            continue
        time_seq.append(float(d.get("t", 0.0)))
        global_notes_seq.append(tuple(d.get("global_notes", []) or []))

        fingers = d.get("fingers", {}) or {}
        for finger_name, fv in fingers.items():
            if not isinstance(fv, dict):
                continue
            z = fv.get("z", None)
            note = fv.get("note", None)
            if z is None:
                continue
            if note is None:
                z_hover[finger_name].append(float(z))
            else:
                z_touch[finger_name].append(float(z))

    print("\n=== Hover vs Touch (z) ===")
    fingers_all = sorted(set(z_hover.keys()) | set(z_touch.keys()))
    for fn in fingers_all:
        zh = np.array(z_hover[fn], dtype=float)
        zt = np.array(z_touch[fn], dtype=float)
        print(f"\n[{fn}]")
        print(" hover_n:", int(len(zh)), " touch_n:", int(len(zt)))
        if len(zh):
            print(" hover_median:", float(np.median(zh)), " hover_p10/p90:", pct(zh, 10), pct(zh, 90))
        if len(zt):
            print(" touch_median:", float(np.median(zt)), " touch_p10/p90:", pct(zt, 10), pct(zt, 90))
        if len(zh) and len(zt):
            print(" median_separation (touch-hover):", float(np.median(zt) - np.median(zh)))

    # --- NOTE ON/OFF desde global_notes
    print("\n=== Note events from global_notes ===")
    events = []  # (time, note, type)
    prev = set()
    for ti, notes in zip(time_seq, global_notes_seq):
        cur = set(notes)
        on = cur - prev
        off = prev - cur
        for n in sorted(on):
            events.append((ti, int(n), "on"))
        for n in sorted(off):
            events.append((ti, int(n), "off"))
        prev = cur

    on_count = sum(1 for e in events if e[2] == "on")
    print("note_on_count:", int(on_count))

    # duraciones (on->off)
    last_on = {}
    durations = []
    for ti, n, typ in events:
        if typ == "on":
            last_on[n] = ti
        elif typ == "off" and n in last_on:
            durations.append(ti - last_on[n])
            del last_on[n]

    dur = np.array(durations, dtype=float)
    if len(dur):
        print("durations_count:", int(len(dur)))
        print("duration_median(s):", float(np.median(dur)))
        print("duration_p05/p95(s):", pct(dur, 5), pct(dur, 95))
    else:
        print("No se pudieron calcular duraciones (faltan OFF o no hay eventos).")

    # rebotes: on-off-on <=150ms
    bounce_thresh = 0.15
    by_note = defaultdict(list)
    for ti, n, typ in events:
        by_note[n].append((ti, typ))

    bounces = 0
    for n, seq in by_note.items():
        for i in range(2, len(seq)):
            t0, a = seq[i - 2]
            t1, b = seq[i - 1]
            t2, c = seq[i]
            if a == "on" and b == "off" and c == "on":
                if (t2 - t0) <= bounce_thresh:
                    bounces += 1
    print("bounces(on-off-on <=150ms):", int(bounces))

if __name__ == "__main__":
    main()