from math import exp, log, fsum, sqrt
from statistics import median, mean, quantiles

from .radius_model import score_kernel



def explain_bead_kernel(fit, calibration, replay, live):
    archive, bandwidth = fit.parameters
    results = []
    for segment in live:
        nearest = []
        for key, line, vector, quality in archive:
            distance = fsum((left-right)**2 for left,right in zip(vector,segment.values,strict=True))
            tier = .32 if line != segment.cohort else 0.
            nearest.append((distance+tier,key,line,quality))
        closest, source, line, historic = min(nearest)
        transfer = int(line != segment.cohort)
        results.append({'巡检点':segment.key,'历史参照点':source,'参照线路':line,'历史衰减':round(historic,2),
                        '近邻距':round(sqrt(closest),3),'跨线路参照':bool(transfer),'带宽尺度':round(sqrt(bandwidth),3)})
    return sorted(results,key=lambda row:(-row['近邻距'],row['巡检点']))[:12]
