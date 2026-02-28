# src/paper/epipolar_residual_minY.py
import json, glob, os
import numpy as np
import cv2

# === CONFIG ===
JSON_PATH = r"camcalibration\calibration.json"
LEFT_GLOB  = r"camcalibration\images\left\*.jpg"
RIGHT_GLOB = r"camcalibration\images\right\*.jpg"
PATTERN = (7, 7)  # esquinas internas (cols, rows)
# ==============

def pct(x, p):
    return float(np.percentile(x, p)) if len(x) else float("nan")

def load_calib(path):
    data = json.load(open(path, "r", encoding="utf-8"))
    K1 = np.array(data["left_camera"]["camera_matrix"], dtype=np.float64)
    D1 = np.array(data["left_camera"]["distortion_coeffs"][0], dtype=np.float64)
    K2 = np.array(data["right_camera"]["camera_matrix"], dtype=np.float64)
    D2 = np.array(data["right_camera"]["distortion_coeffs"][0], dtype=np.float64)

    R1 = np.array(data["stereo"]["rectification"]["R1"], dtype=np.float64)
    R2 = np.array(data["stereo"]["rectification"]["R2"], dtype=np.float64)
    P1 = np.array(data["stereo"]["rectification"]["P1"], dtype=np.float64)
    P2 = np.array(data["stereo"]["rectification"]["P2"], dtype=np.float64)
    return K1, D1, K2, D2, R1, R2, P1, P2

def pair_by_basename(left_files, right_files):
    L = {os.path.basename(p): p for p in left_files}
    R = {os.path.basename(p): p for p in right_files}
    keys = sorted(set(L.keys()) & set(R.keys()))
    return [(L[k], R[k]) for k in keys]

def find_corners(gray, pattern):
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
    ok, corners = cv2.findChessboardCorners(gray, pattern, flags)
    if not ok:
        return None

    term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    corners = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), term)
    return corners.astype(np.float64)

def main():
    K1, D1, K2, D2, R1, R2, P1, P2 = load_calib(JSON_PATH)

    left_files = sorted(glob.glob(LEFT_GLOB))
    right_files = sorted(glob.glob(RIGHT_GLOB))
    pairs = pair_by_basename(left_files, right_files)

    residuals = []
    used_pairs = 0
    used_points = 0

    for lp, rp in pairs:
        imL = cv2.imread(lp, cv2.IMREAD_GRAYSCALE)
        imR = cv2.imread(rp, cv2.IMREAD_GRAYSCALE)
        if imL is None or imR is None:
            continue

        cL = find_corners(imL, PATTERN)
        cR = find_corners(imR, PATTERN)
        if cL is None or cR is None:
            continue
        if len(cL) != len(cR):
            continue

        # Rectificar puntos a coordenadas pixel en el plano rectificado
        rL = cv2.undistortPoints(cL, K1, D1, R=R1, P=P1)  # Nx1x2
        rR = cv2.undistortPoints(cR, K2, D2, R=R2, P=P2)  # Nx1x2

        YL = rL[:,0,1]  # y rectificada de puntos en L
        YR = rR[:,0,1]  # y rectificada de puntos en R

        # Para cada y_L, encuentra la y_R más cercana (min |yL - yR|)
        dv = []
        for yL in YL:
            dv.append(np.min(np.abs(YR - yL)))
        dv = np.array(dv, dtype=np.float64)

        residuals.append(dv)
        used_pairs += 1
        used_points += dv.size

    if not residuals:
        print("No se pudieron calcular residuales (no se detectaron esquinas).")
        return

    res = np.concatenate(residuals)
    print("pairs_used:", used_pairs)
    print("points_used:", used_points)
    print("median_abs_dv(px):", float(np.median(res)))
    print("p95_abs_dv(px):", pct(res, 95))

if __name__ == "__main__":
    main()