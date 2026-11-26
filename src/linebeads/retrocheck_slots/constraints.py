from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from .contracts import Job


@dataclass(frozen=True, slots=True)
class WorkOrder:
    job: Job
    assessment: Any

    def __post_init__(self):
        if self.job.key != self.assessment.raw.key:
            raise ValueError('处置工位与单据不匹配')


def apply_retrocheck_slots(roads, admit: Callable, wait: Callable):
    probe_tally = Counter()
    for segment in roads:
        light, age, humidity, cars, beads, surface = segment.assessment.raw.input_values
        route = segment.job.cohort
        required = 2 if humidity>=55 or cars>=52 else 1
        if surface<=5 and humidity>58:
            wait(segment, 'WET_SURFACE_PRECISION', '先记录湿面夜温，等可测窗口')
            continue
        if probe_tally[route]+required > 5:
            wait(segment, 'RETROREFLECTOMETER_QUOTA', '该路线的夜间复测配时已满')
        elif admit(segment):
            probe_tally[route] += required
