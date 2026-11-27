from dataclasses import dataclass
from math import isfinite
from ..lane_samples.contracts import LinebeadsRecord as RawObservation

RAW_KEYS = ('retro_cd', 'age_days', 'wet_pct', 'traffic_k', 'beads_g', 'surface_c')
FEATURE_KEYS = ('retention', 'wet_loss', 'grain_coverage', 'traffic_exposure', 'thermal_mismatch')
FEATURE_NAMES = ('龄期反光余量', '车流潮湿协变', '湿面等效玻璃珠', '累计车流暴露', '温度偏离')
# 特征依赖的原始量测，用于判断训练包络偏离是否由补值引起。
FEATURE_RAW_INPUTS = {
    'retention': ('retro_cd', 'age_days'),
    'wet_loss': ('wet_pct', 'traffic_k'),
    'grain_coverage': ('beads_g', 'wet_pct'),
    'traffic_exposure': ('age_days', 'traffic_k'),
    'thermal_mismatch': ('surface_c',),
}


@dataclass(frozen=True, slots=True)
class Imputation:
    field: str
    value: float
    basis: str
    records: int
    verdict: str | None = None

    @property
    def basis_label(self):
        return '同区成熟中位' if self.basis == 'ZONE' else '全班历史中位'

    @property
    def masked(self):
        return self.verdict == 'FILL_EXCEEDS_TRAINING_RANGE'

    def evidence(self):
        return {'缺测字段': self.field, '补入值': round(self.value, 4),
                '补值依据': self.basis_label,
                '同区成熟记录': self.records, '推出训练范围': self.masked,
                '审查结论': '保留实测转人工' if self.verdict else '可据补值派工'}


def missing_review_reason(fills):
    """Return the manual-review reason for a partially imputed ticket, if any.

    Zone fills with adequate same-zone coverage keep a ticket dispatchable. It is
    only held back when the fill basis is unsafe, in either of two ways:

    * ``FILL_EXCEEDS_TRAINING_RANGE`` — the same-zone median would land a modelled
      feature past the frozen envelope, which could hide a low-reflectance segment
      behind a normal-looking estimate; the zone basis is rejected;
    * ``FILL_ZONE_COVERAGE_LOW`` — the same-zone mature history is too thin to
      stand behind a local median, so the pooled median must stand in and zone
      behaviour is unverified.

    When a ticket carries several unsafe fills the range verdict is reported
    first, because hiding a dark segment is the more serious risk.
    """
    verdicts = {fill.verdict for fill in fills if fill.verdict}
    for reason in ('FILL_EXCEEDS_TRAINING_RANGE', 'FILL_ZONE_COVERAGE_LOW'):
        if reason in verdicts:
            return reason
    return None


@dataclass(frozen=True, slots=True)
class FeatureState:
    fill: tuple[float, ...]
    zone_fill: tuple[tuple[str, tuple[float | None, ...], tuple[int, ...]], ...]
    offsets: tuple[float, ...]
    scales: tuple[float, ...]
    floor: tuple[float, ...]
    ceil: tuple[float, ...]
    fill_version: str
    fingerprint: str

    def __post_init__(self):
        if len(self.fill) != len(RAW_KEYS):
            raise ValueError('补值向量维数与字段表不匹配')
        if any(len(column) != len(FEATURE_KEYS) for column in (self.offsets, self.scales, self.floor, self.ceil)):
            raise ValueError('特征状态维数不匹配')
        if min(self.scales) <= 0:
            raise ValueError('特征尺度必须为正')
        if not self.fill_version:
            raise ValueError('补值依据缺少版本')
        names = [name for name, _, _ in self.zone_fill]
        if names != sorted(set(names)):
            raise ValueError('分区补值表须按分区名唯一排序')
        for _, values, counts in self.zone_fill:
            if len(values) != len(RAW_KEYS) or len(counts) != len(RAW_KEYS):
                raise ValueError('分区补值表维数与字段表不匹配')
            if any(number is not None and count <= 0 for number, count in zip(values, counts, strict=True)):
                raise ValueError('分区补值中位数缺少对应成熟记录')

    def zone_for(self, cohort):
        for name, values, counts in self.zone_fill:
            if name == cohort:
                return values, counts
        return None, (0,) * len(RAW_KEYS)


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
    fills: tuple[Imputation, ...] = ()

    def review_reason(self):
        """Return a manual-review reason when the imputed ticket cannot be dispatched on."""
        return missing_review_reason(self.fills)

    def fill_evidence(self):
        return [fill.evidence() for fill in self.fills]


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
