from app.schemas.claims import AnalysisBlockedReasonResponse


class AnalysisConfirmationBlockedError(Exception):
    def __init__(self, reasons: list[AnalysisBlockedReasonResponse]):
        super().__init__("Analysis confirmation is blocked")
        self.reasons = reasons

    def detail(self) -> dict[str, object]:
        return {
            "message": str(self),
            "blocked_reasons": [reason.model_dump(mode="json") for reason in self.reasons],
        }
