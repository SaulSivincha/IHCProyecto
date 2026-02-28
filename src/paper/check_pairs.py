import glob, os

L = sorted(glob.glob(r"camcalibration\images\left\*.jpg"))
R = sorted(glob.glob(r"camcalibration\images\right\*.jpg"))

print("L:", len(L), "R:", len(R))

bad = 0
for i in range(min(len(L), len(R))):
    ln = os.path.basename(L[i]).replace("left", "")
    rn = os.path.basename(R[i]).replace("right", "")
    if ln != rn:
        bad += 1
        if bad < 10:
            print("mismatch:", os.path.basename(L[i]), os.path.basename(R[i]))

print("total_mismatches:", bad)