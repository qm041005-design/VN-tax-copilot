"""Safety primitives for VN-tax-copilot (SCRUM-11)."""
from .abstention import AbstentionDecision, EvidenceAssessment, decide_abstention
from .redaction import RedactionResult, redact_text

__all__ = [
    "AbstentionDecision", "EvidenceAssessment", "decide_abstention",
    "RedactionResult", "redact_text",
]
from .pipeline import PreparedResearch, prepare_research

__all__ += ["PreparedResearch", "prepare_research"]
from .research import (
    Claim, GeneratedResearch, ResearchContext, ResearchResult,
    SafeResearchInput, run_guarded_research, validate_citations,
)

__all__ += [
    "Claim", "GeneratedResearch", "ResearchContext", "ResearchResult",
    "SafeResearchInput", "run_guarded_research", "validate_citations",
]
from .contract import SECTION_NAMES, to_contract, validate_output

__all__ += ["SECTION_NAMES", "to_contract", "validate_output"]
from .prompt_adapter import make_prompt_generator

__all__ += ["make_prompt_generator"]
