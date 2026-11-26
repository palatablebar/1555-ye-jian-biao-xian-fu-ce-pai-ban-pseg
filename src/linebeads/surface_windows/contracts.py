from dataclasses import dataclass
from ..lane_samples.contracts import LinebeadsRecord


@dataclass(frozen=True, slots=True, order=True)
class Span:
    begin: int
    end: int

    def __post_init__(self):
        if type(self.begin) is not int or type(self.end) is not int or self.begin >= self.end:
            raise ValueError('窗口边界应为递增的整数日')

    def __contains__(self, day):
        return self.begin <= day < self.end


@dataclass(frozen=True, slots=True)
class WindowRule:
    train: Span
    calibration: Span
    replay: Span
    live: Span
    as_of: int
    allow_censor: bool

    def __post_init__(self):
        spans = (self.train, self.calibration, self.replay, self.live)
        if any(left.end > right.begin for left, right in zip(spans, spans[1:])):
            raise ValueError('分窗重叠')
        if self.as_of not in self.live:
            raise ValueError('截止日必须处于当班窗口')

    def folds(self):
        return ('train', self.train), ('calibration', self.calibration), ('replay', self.replay)

    @classmethod
    def standard(cls, *, allow_censor=False):
        train, switch, calibrate, lock, replay, replay_end, shift = (0, 40, 43, 62, 65, 85, 88)
        return cls(Span(train,switch),Span(calibrate,lock),Span(replay,replay_end),Span(shift,3651),96,allow_censor)


@dataclass(frozen=True, slots=True)
class FoldSummary:
    name: str
    count: int
    cohort_count: int
    censored: int
    first_day: int | None
    last_day: int | None


@dataclass(frozen=True, slots=True)
class Chronology:
    train: tuple[LinebeadsRecord, ...]
    calibration: tuple[LinebeadsRecord, ...]
    replay: tuple[LinebeadsRecord, ...]
    live: tuple[LinebeadsRecord, ...]
    excluded: tuple[tuple[str, str], ...]

    def partitions(self):
        return ('train', self.train), ('calibration', self.calibration), ('replay', self.replay), ('live', self.live)

    def check_conservation(self, total):
        keys = [record.key for _, entries in self.partitions() for record in entries]
        keys.extend(key for key, _ in self.excluded)
        if len(keys) != total or len(set(keys)) != len(keys):
            raise ArithmeticError('分窗单据遗失或重复')
