from dataclasses import dataclass, field
from typing import List

RANK_ORDER = {"LTA": 1, "2LT": 2, "1SG": 3, "2SG": 4, "3SG": 5}
INITIATOR_APPTS = {"OC", "CSM", "2IC"}
# 2SG is only treated as senior if tagged PL SGT — checked via Person.is_senior property
_BASE_SENIOR_RANKS = {"LTA", "2LT", "1SG"}
# Maximum outbound calls a 3SG can be boosted to
MAX_3SG_CALL_LIMIT = 4

def rank_level(rank: str) -> int:
    return RANK_ORDER.get(rank.strip().upper(), 6)

def _is_pl_appt(appt: str) -> bool:
    a = appt.strip().upper()
    a_nospace = a.replace(" ", "").replace("-", "")
    # Match any variant containing both "PL" and "SGT" (e.g. "PL SGT", "PL-SGT", "PLSGT", "SGT PL")
    tokens = set(a.replace("-", " ").split())
    is_pl_sgt = "PLSGT" in a_nospace
    # Match PL COMD variants (e.g. "PL COMD", "PLCOMD", "PL-COMD")
    is_pl_comd = "PLCOMD" in a_nospace
    # Known PL COMD equivalents
    PL_COMD_EQUIVALENTS = {"BSO"}
    is_equivalent = any(equiv in tokens for equiv in PL_COMD_EQUIVALENTS)
    return is_pl_sgt or is_pl_comd or is_equivalent

@dataclass
class Person:
    rank: str
    name: str
    platoon: str
    appt: str
    available: bool
    rank_level: int = field(init=False)
    is_initiator: bool = field(init=False)
    is_pl_appt: bool = field(init=False)
    calls: List["Person"] = field(default_factory=list)
    called_by: List["Person"] = field(default_factory=list)

    def __post_init__(self):
        self.rank_level = rank_level(self.rank)
        self.is_initiator = self.appt.strip().upper() in INITIATOR_APPTS
        self.is_pl_appt = _is_pl_appt(self.appt)

    @property
    def is_senior(self) -> bool:
        """True for LTA/2LT/1SG always; True for 2SG only if tagged PL SGT.
        Non-PL-SGT 2SGs are treated like 3SGs for calling rules and limits."""
        r = self.rank.strip().upper()
        if r in _BASE_SENIOR_RANKS:
            return True
        if r == "2SG" and self.is_pl_appt:
            return True
        return False

    @property
    def effective_rank_level(self) -> int:
        """Non-PL-SGT 2SGs are demoted to rank_level 5 (same as 3SG)."""
        if self.rank.strip().upper() == "2SG" and not self.is_pl_appt:
            return 5
        return self.rank_level

    def call_limit(self) -> int:
        base = 4
        limit = base + getattr(self, '_call_limit_boost', 0)
        # 3SGs may be boosted but are capped at MAX_3SG_CALL_LIMIT
        if self.rank.strip().upper() == "3SG":
            limit = min(limit, MAX_3SG_CALL_LIMIT)
        return limit

    def can_call_more(self) -> bool:
        return len(self.calls) < self.call_limit()

    def can_be_called_more(self) -> bool:
        if self.is_initiator:
            return True
        return len(self.called_by) < 2

    def __repr__(self):
        return f"{self.rank} {self.name} (Plt {self.platoon})"