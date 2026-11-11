"""Safety primitives for VN-tax-copilot (SCRUM-11)."""
from .abstention import AbstentionDecision, EvidenceAssessment, decide_abstention
from .redaction import RedactionResult, redact_text

__all__ = [
    "AbstentionDecision", "EvidenceAssessment", "decide_abstention",
    "RedactionResult", "redact_text",
]
from .pipeline import PreparedResearch, prepare_research

__all__ += ["PreparedResearch", "prepare_research"]
