from dataclasses import dataclass
from typing import Any

MODEL_NAME = 'RBF 局部反光衰减回归'
RISK_MODEL = False


@dataclass(frozen=True, slots=True)
class Fit:
    name: str
    feature: str
    fingerprint: str
    parameters: Any
    evidence: tuple[tuple[str, float | int], ...]

    def __post_init__(self):
        if not self.feature or not self.fingerprint:
            raise ValueError('模型缺少训练凭证')
        if not self.evidence:
            raise ValueError('模型未登记审计信息')


@dataclass(frozen=True, slots=True)
class Prediction:
    key: str
    cohort: str
    day: int
    score: float
    contributions: tuple[float, ...]
    missing: tuple[str, ...]
    excursions: tuple[str, ...]
    outcome: float | None
    observed: bool
    input_values: tuple[float, ...]

    def evidence(self):
        return {'单号': self.key, '分组': self.cohort, '工作日': self.day, '估计': self.score,
                '贡献': self.contributions, '缺测': self.missing, '偏离': self.excursions}
