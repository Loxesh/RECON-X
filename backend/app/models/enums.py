
from enum import Enum


class SourceType(str, Enum):
    BANK = "BANK"
    LEDGER = "LEDGER"
    GATEWAY = "GATEWAY"


class TransactionDirection(str, Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class TransactionValidity(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"


class TransactionMatchStatus(str, Enum):
    UNMATCHED = "UNMATCHED"


class MatchType(str, Enum):
    EXACT = "EXACT"


class MatchOrigin(str, Enum):
    DETERMINISTIC_DECISION = "DETERMINISTIC_DECISION"


class ConfidenceLabel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ApprovalDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class AuditOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
