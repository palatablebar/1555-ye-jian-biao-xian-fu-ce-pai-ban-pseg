from dataclasses import dataclass

FIELDS = {'retro_cd': ('当前反光系数', 'mcd', 70, 520),
 'age_days': ('涂覆后天数', '天', 4, 450),
 'wet_pct': ('潮湿面积', '%', 0, 92),
 'traffic_k': ('日车辆', '千辆', 1, 75),
 'beads_g': ('玻璃珠投放量', 'g/m²', 165, 435),
 'surface_c': ('路表温度', '℃', 2, 37)}
LIMITS = {'result_max': 10000}


class MeasureIssue(ValueError):
    def __init__(self, field: str, code: str):
        super().__init__(f'{field}:{code}')
        self.field = field
        self.code = code


@dataclass(frozen=True, slots=True)
class LinebeadsRecord:
    key: str
    cohort: str
    day: int
    received: int
    revision: int
    result_day: int | None
    outcome: float | None
    observed: bool
    retro_cd: float | None
    age_days: float | None
    wet_pct: float | None
    traffic_k: float | None
    beads_g: float | None
    surface_c: float | None

    def signature(self):
        return (self.key, self.cohort, self.day, self.revision, self.result_day, self.outcome, self.observed,
                *(getattr(self, key) for key in FIELDS))


@dataclass(frozen=True, slots=True)
class Issue:
    source_row: int
    key: str
    field: str
    code: str

    def evidence(self):
        return {'行号': self.source_row, '单号': self.key, '字段': FIELDS.get(self.field, (self.field,))[0],
                '原因': self.code}


@dataclass(frozen=True, slots=True)
class DecodeResult:
    entries: tuple[LinebeadsRecord, ...]
    issues: tuple[Issue, ...]
    source_rows: int
