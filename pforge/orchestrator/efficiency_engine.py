from __future__ import annotations
from .state_bus import PuzzleState

class EfficiencyEngine:
    def __init__(self, consts: dict) -> None:
        self.gamma = consts.get("gamma", 1.0)
        self.alpha = consts.get("alpha", 1.0)
        self.lambda_ = consts.get("lambda", 2.0)
        self.beta = consts.get("beta", 1.0)
        self.eta = consts.get("eta", 1.5)
        self.theta = consts.get("theta", 2.0)
        self.total_pieces: int | None = None

    def compute(self, s: PuzzleState) -> float:
        if s is None:
            return 0.0

        P = self.total_pieces or (s.gaps + s.misfits + s.false_pieces)
        if P == 0:
            P = 1

        denominator = (
            s.tick
            + (s.gaps + self.gamma * s.misfits + self.alpha * s.false_pieces)
            + self.lambda_ * s.risk
            + self.beta * s.backtracks
            + self.eta * s.entropy
            - self.theta * s.phi
        )
        return max(P / max(denominator, 1.0), 0.0)
