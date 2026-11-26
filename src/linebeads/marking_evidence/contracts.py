from dataclasses import dataclass

POLICY_VERSION = 'linebeads.20261125.v1'


@dataclass(frozen=True, slots=True)
class LedgerCheck:
    raw: int
    isolated: int
    mature_excluded: int
    scored: int
    capacity: int
    resource_used: int
    balance: int
    states: tuple[tuple[str, int], ...]

    def __post_init__(self):
        if self.capacity != self.resource_used + self.balance:
            raise ArithmeticError('不能出具额度不平的凭证')
        if self.scored != sum(number for _, number in self.states):
            raise ArithmeticError('不能出具单据数量不平的凭证')


@dataclass(frozen=True, slots=True)
class BatchReceipt:
    stamp: str
    batch_hash: str
    policy_hash: str
    totals: LedgerCheck
    decisions: tuple[tuple[str, str, int, str, float], ...]
