"""Read-only canonical Decision Board proposal generation for Lab OS."""

from .builder import build_canonical_decision_proposal
from .models import CanonicalProposalResult

__all__ = ["CanonicalProposalResult", "build_canonical_decision_proposal"]
