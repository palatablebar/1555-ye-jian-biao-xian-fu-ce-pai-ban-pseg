from dataclasses import dataclass
from math import isfinite
from ..lane_samples.contracts import LinebeadsRecord as RawObservation

RAW_KEYS = ('retro_cd', 'age_days', 'wet_pct', 'traffic_k', 'beads_g', 'surface_c')
FEATURE_KEYS = ('retention', 'wet_loss', 'grain_coverage', 'traffic_exposure', 'thermal_mismatch')
FEATURE_NAMES = ('龄期反光余量', '车流潮湿协变', '湿面等效玻璃珠', '累计车流暴露', '温度偏离')


@dataclass(frozen=True, slots=True)
class FeatureState:
    fill: tuple[float, ...]
    offsets: tuple[float, ...]
    scales: tuple[float, ...]
    floor: tuple[float, ...]
    ceil: tuple[float, ...]
    fingerprint: str

    def __post_init__(self):
        if len(self.fill) != len(RAW_KEYS):
            raise ValueError('补值向量维数与字段表不匹配')
        if any(len(column) != len(FEATURE_KEYS) for column in (self.offsets, self.scales, self.floor, self.ceil)):
            raise ValueError('特征状态维数不匹配')
        if min(self.scales) <= 0:
            raise ValueError('特征尺度必须为正')


@dataclass(frozen=True, slots=True)
class FeatureVector:
    key: str
    cohort: str
    day: int
    values: tuple[float, ...]
    factors: tuple[float, ...]
    missing: tuple[str, ...]
    excursions: tuple[str, ...]
    outcome: float | None
    observed: bool
    input_values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class PreparedRuns:
    train: tuple[FeatureVector, ...]
    calibration: tuple[FeatureVector, ...]
    replay: tuple[FeatureVector, ...]
    live: tuple[FeatureVector, ...]

    def segments(self):
        return tuple((name, getattr(self, name)) for name in ('train', 'calibration', 'replay', 'live'))


@dataclass(frozen=True, slots=True)
class Proposal:
    name: str
    field: str
    before: float
    after: float
    work: int

    def __post_init__(self):
        if self.before == self.after or not isfinite(self.after) or self.work < 0:
            raise ValueError('推演动作需要实质变动和有效额度')

    def evidence(self):
        return {'情形': self.name, '变更项': self.field, '原值': self.before,
                '置换值': self.after, '用量': self.work}

@dataclass(frozen=True, slots=True)
class ReflectionFactors:
    light_reserve: float
    wet_traffic: float
    network_wear: float
    bead_deficit: float
    water_surface: float
    shift_temperature: float
    remaining_quality: float
    field_exposure: float

    def __post_init__(self):
        if not all(isfinite(amount) for amount in (self.light_reserve, self.wet_traffic, self.network_wear, self.bead_deficit, self.water_surface, self.shift_temperature, self.remaining_quality, self.field_exposure)):
            raise ValueError('标线路段存在无效的作业量测')

    def explain(self, labels=None):
        return (
            ('距雨夜基准反光量', round(self.light_reserve, 4)),
            ('湿面预计车流', round(self.wet_traffic, 4)),
            ('整段累计车流', round(self.network_wear, 4)),
            ('相对低投放余量', round(self.bead_deficit, 4)),
            ('相对湿膜损失因子', round(self.water_surface, 4)),
            ('路表离标定温差', round(self.shift_temperature, 4)),
            ('折算干面反光余量', round(self.remaining_quality, 4)),
            ('养护复查压力', round(self.field_exposure, 4)),
        )
