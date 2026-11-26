from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DriftBand:
    name: str
    edges: tuple[float, ...]
    counts: tuple[int, ...]

    def __post_init__(self):
        if len(self.counts) != len(self.edges) + 1:
            raise ValueError('区间计数不完整')


@dataclass(frozen=True, slots=True)
class ReferenceProfile:
    signature: str
    bands: tuple
    cohorts: tuple | dict | set
    samples: int

    def __post_init__(self):
        if not self.signature or self.samples <= 0:
            raise ValueError('缺少训练参考版本或实绩数')


@dataclass(frozen=True, slots=True)
class ShiftReport:
    samples: int
    signals: tuple[tuple[str, float], ...]
    novel: tuple[str, ...]
    domain: tuple[str, ...]
    status: str
