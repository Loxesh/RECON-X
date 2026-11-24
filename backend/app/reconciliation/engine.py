"""Deterministic dual-track reconciliation engine.

Bank transactions are reconciled independently against the ledger.
Gateway transactions are reconciled independently against the ledger.

The engine does not persist data, approve financial actions, or generate
aggregate candidate groups automatically.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping

from app.models.enums import SourceType
from app.reconciliation.aggregate_match import match_aggregate_group
from app.reconciliation.discrepancy_detector import (
    DiscrepancyInput,
    detect_discrepancies,
)
from app.reconciliation.duplicate_detector import (
    DuplicateEvidence,
    detect_duplicates,
)
from app.reconciliation.exception_classifier import (
    ClassifiedException,
    classify_discrepancies,
)
from app.reconciliation.exact_match import match_exact_pair
from app.reconciliation.fuzzy_match import match_fuzzy_pair
from app.reconciliation.missing_detector import (
    MissingEvidence,
    detect_missing_transactions,
)
from app.reconciliation.rules import MatchingRuleset
from app.reconciliation.schemas import (
    MatchEvidence,
    MatchOutcome,
    MatchingPairInput,
    MatchingResult,
    MatchingTransaction,
)
from app.reconciliation.status_calculator import (
    ConsolidatedStatus,
    TrackStatus,
    calculate_consolidated_status,
    calculate_track_status,
    transaction_key,
)


@dataclass(frozen=True)
class AggregateCandidateGroup:
    """An explicitly proposed aggregate group."""

    left_transaction_ids: tuple[str, ...]
    right_transaction_ids: tuple[str, ...]


@dataclass(frozen=True)
class TrackResult:
    """Complete result of one independent reconciliation track."""

    track_name: str
    source_type: SourceType
    matches: tuple[MatchingResult, ...]
    aggregate_results: tuple[MatchingResult, ...]
    duplicate_evidence: tuple[DuplicateEvidence, ...]
    missing_evidence: tuple[MissingEvidence, ...]
    exceptions: tuple[ClassifiedException, ...]
    outcomes: Mapping[str, MatchOutcome]
    status: TrackStatus
    pending_transaction_ids: tuple[str, ...]
    ruleset_version: str
    ruleset_hash: str


@dataclass(frozen=True)
class ReconciliationResult:
    """Complete dual-track reconciliation result."""

    bank_ledger: TrackResult
    gateway_ledger: TrackResult
    consolidated_status: ConsolidatedStatus
    ruleset_version: str
    ruleset_hash: str


def _validate_source_collection(
    transactions: tuple[MatchingTransaction, ...],
    expected_source: SourceType,
    collection_name: str,
) -> None:
    ids = [item.transaction_id for item in transactions]

    if len(ids) != len(set(ids)):
        raise ValueError(f"{collection_name} contains duplicate transaction IDs.")

    if any(item.source_type != expected_source for item in transactions):
        raise ValueError(f"{collection_name} contains an unexpected source type.")

    for item in transactions:
        value = item.transaction_date
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Reconciliation requires timezone-aware transaction dates."
            )
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("Transaction dates must be normalized to UTC.")


def _make_pair(
    left: MatchingTransaction,
    right: MatchingTransaction,
    ruleset: MatchingRuleset,
) -> MatchingPairInput:
    return MatchingPairInput(
        left=left,
        right=right,
        ruleset_version=ruleset.version,
        ruleset_hash=ruleset.fingerprint,
    )


def _tolerance_candidate(
    left: MatchingTransaction,
    right: MatchingTransaction,
    ruleset: MatchingRuleset,
) -> MatchingResult | None:
    """Evaluate a same-reference amount difference under configured tolerances."""

    left_reference = (left.reference_norm or left.transaction_reference or "")
    right_reference = (right.reference_norm or right.transaction_reference or "")

    left_reference = " ".join(left_reference.strip().upper().split())
    right_reference = " ".join(right_reference.strip().upper().split())

    if not left_reference or left_reference != right_reference:
        return None
    if left.currency != right.currency:
        return None

    if left.source_type == SourceType.BANK or right.source_type == SourceType.BANK:
        date_window = ruleset.bank_ledger_date_window_days
    else:
        date_window = ruleset.gateway_ledger_date_window_days

    date_days = abs(
        (left.transaction_date.date() - right.transaction_date.date()).days
    )
    if date_days > date_window:
        return None

    difference = abs(left.amount - right.amount)
    if difference == 0 or difference > ruleset.suggested_amount_tolerance:
        return None

    auto_confirm = difference <= ruleset.auto_confirm_amount_tolerance

    evidence = MatchEvidence(
        rule_id="TOL_01",
        rule_priority=ruleset.rule_priority.index("TOLERANCE"),
        reason=(
            "Reference, currency, and date conditions agree; the amount "
            "difference is within the configured automatic-confirmation tolerance."
            if auto_confirm
            else
            "Reference, currency, and date conditions agree; the amount "
            "difference is within the suggested tolerance. Human review is required."
        ),
        compared_fields=(
            "reference_norm",
            "currency",
            "transaction_date",
            "amount",
        ),
        observed_values={
            "left_reference": left_reference,
            "right_reference": right_reference,
            "left_amount": str(left.amount),
            "right_amount": str(right.amount),
            "amount_difference": str(difference),
            "currency": left.currency,
            "date_difference_days": str(date_days),
            "date_window_days": str(date_window),
        },
    )

    return MatchingResult(
        outcome=(
            MatchOutcome.CONFIRMED_AUTO
            if auto_confirm
            else MatchOutcome.SUGGESTED
        ),
        rule_id="TOL_01",
        transaction_ids=(left.transaction_id, right.transaction_id),
        evidence=(evidence,),
        candidate_score=None,
        ruleset_version=ruleset.version,
        ruleset_hash=ruleset.fingerprint,
    )


def _resolve_confirmed_candidates(
    candidates: list[MatchingResult],
    ruleset: MatchingRuleset,
) -> tuple[tuple[MatchingResult, ...], tuple[MatchingResult, ...]]:
    """Select mutually unique confirmed pairs; preserve conflicts as ambiguous."""

    left_degree: dict[str, int] = defaultdict(int)
    right_degree: dict[str, int] = defaultdict(int)

    for item in candidates:
        left_id, right_id = item.transaction_ids
        left_degree[left_id] += 1
        right_degree[right_id] += 1

    selected = []
    conflicts = []

    for item in candidates:
        left_id, right_id = item.transaction_ids
        if left_degree[left_id] == 1 and right_degree[right_id] == 1:
            selected.append(item)
        else:
            conflicts.append(
                MatchingResult(
                    outcome=MatchOutcome.AMBIGUOUS,
                    rule_id=item.rule_id,
                    transaction_ids=item.transaction_ids,
                    evidence=item.evidence,
                    candidate_score=item.candidate_score,
                    ruleset_version=ruleset.version,
                    ruleset_hash=ruleset.fingerprint,
                )
            )

    key = lambda item: item.transaction_ids
    return tuple(sorted(selected, key=key)), tuple(sorted(conflicts, key=key))


def _resolve_suggestions(
    candidates: list[MatchingResult],
    ruleset: MatchingRuleset,
) -> tuple[MatchingResult, ...]:
    """Keep a fuzzy suggestion only when it is the unique reciprocal best."""

    if not candidates:
        return ()

    left_scores: dict[str, list[Decimal]] = defaultdict(list)
    right_scores: dict[str, list[Decimal]] = defaultdict(list)

    for item in candidates:
        left_id, right_id = item.transaction_ids
        score = item.candidate_score or Decimal("0")
        left_scores[left_id].append(score)
        right_scores[right_id].append(score)

    left_best = {key: max(values) for key, values in left_scores.items()}
    right_best = {key: max(values) for key, values in right_scores.items()}

    left_best_count: dict[str, int] = defaultdict(int)
    right_best_count: dict[str, int] = defaultdict(int)

    for item in candidates:
        left_id, right_id = item.transaction_ids
        score = item.candidate_score or Decimal("0")
        if score == left_best[left_id]:
            left_best_count[left_id] += 1
        if score == right_best[right_id]:
            right_best_count[right_id] += 1

    results = []
    for item in candidates:
        left_id, right_id = item.transaction_ids
        score = item.candidate_score or Decimal("0")

        is_unique_reciprocal_best = (
            score == left_best[left_id]
            and score == right_best[right_id]
            and left_best_count[left_id] == 1
            and right_best_count[right_id] == 1
        )

        if is_unique_reciprocal_best and item.outcome != MatchOutcome.AMBIGUOUS:
            results.append(item)
        else:
            results.append(
                MatchingResult(
                    outcome=MatchOutcome.AMBIGUOUS,
                    rule_id=item.rule_id,
                    transaction_ids=item.transaction_ids,
                    evidence=item.evidence,
                    candidate_score=item.candidate_score,
                    ruleset_version=ruleset.version,
                    ruleset_hash=ruleset.fingerprint,
                )
            )

    return tuple(sorted(results, key=lambda item: item.transaction_ids))


def _build_track(
    *,
    track_name: str,
    left_transactions: tuple[MatchingTransaction, ...],
    right_transactions: tuple[MatchingTransaction, ...],
    left_source: SourceType,
    right_source: SourceType,
    ruleset: MatchingRuleset,
    aggregate_candidates: tuple[AggregateCandidateGroup, ...],
) -> TrackResult:
    left_by_id = {item.transaction_id: item for item in left_transactions}
    right_by_id = {item.transaction_id: item for item in right_transactions}

    matches: list[MatchingResult] = []
    aggregate_results: list[MatchingResult] = []
    consumed_left: set[str] = set()
    consumed_right: set[str] = set()
    pending_left: set[str] = set()
    pending_right: set[str] = set()

    # Passes 1 and 2: exact stable ID and approved reference matching.
    exact_candidates = []
    for left in sorted(left_transactions, key=lambda item: item.transaction_id):
        for right in sorted(right_transactions, key=lambda item: item.transaction_id):
            result = match_exact_pair(_make_pair(left, right, ruleset), ruleset)
            if result.outcome == MatchOutcome.CONFIRMED_AUTO:
                exact_candidates.append(result)

    selected, conflicts = _resolve_confirmed_candidates(exact_candidates, ruleset)
    matches.extend(selected)
    matches.extend(conflicts)

    for item in selected:
        consumed_left.add(item.transaction_ids[0])
        consumed_right.add(item.transaction_ids[1])
    for item in conflicts:
        pending_left.add(item.transaction_ids[0])
        pending_right.add(item.transaction_ids[1])

    # Tolerance candidates: unique automatic matches can be confirmed;
    # suggested or competing candidates remain pending for human review.
    tolerance_candidates = []
    for left in left_transactions:
        if left.transaction_id in consumed_left or left.transaction_id in pending_left:
            continue
        for right in right_transactions:
            if right.transaction_id in consumed_right or right.transaction_id in pending_right:
                continue
            candidate = _tolerance_candidate(left, right, ruleset)
            if candidate is not None:
                tolerance_candidates.append(candidate)

    tolerance_auto = [
        item for item in tolerance_candidates
        if item.outcome == MatchOutcome.CONFIRMED_AUTO
    ]
    selected, conflicts = _resolve_confirmed_candidates(tolerance_auto, ruleset)
    matches.extend(selected)
    matches.extend(conflicts)

    for item in selected:
        consumed_left.add(item.transaction_ids[0])
        consumed_right.add(item.transaction_ids[1])
    for item in conflicts:
        pending_left.add(item.transaction_ids[0])
        pending_right.add(item.transaction_ids[1])

    tolerance_suggestions = [
        item for item in tolerance_candidates
        if item.outcome == MatchOutcome.SUGGESTED
    ]
    tolerance_left_degree: dict[str, int] = defaultdict(int)
    tolerance_right_degree: dict[str, int] = defaultdict(int)
    for item in tolerance_suggestions:
        tolerance_left_degree[item.transaction_ids[0]] += 1
        tolerance_right_degree[item.transaction_ids[1]] += 1

    for item in tolerance_suggestions:
        left_id, right_id = item.transaction_ids
        if tolerance_left_degree[left_id] > 1 or tolerance_right_degree[right_id] > 1:
            item = MatchingResult(
                outcome=MatchOutcome.AMBIGUOUS,
                rule_id=item.rule_id,
                transaction_ids=item.transaction_ids,
                evidence=item.evidence,
                candidate_score=item.candidate_score,
                ruleset_version=ruleset.version,
                ruleset_hash=ruleset.fingerprint,
            )
        matches.append(item)
        pending_left.add(left_id)
        pending_right.add(right_id)

    # Pass 3: fuzzy candidates. Fuzzy results are never auto-confirmed.
    fuzzy_candidates = []
    for left in left_transactions:
        if left.transaction_id in consumed_left or left.transaction_id in pending_left:
            continue
        for right in right_transactions:
            if right.transaction_id in consumed_right or right.transaction_id in pending_right:
                continue
            result = match_fuzzy_pair(_make_pair(left, right, ruleset), ruleset)
            if result.outcome in {MatchOutcome.SUGGESTED, MatchOutcome.AMBIGUOUS}:
                fuzzy_candidates.append(result)

    fuzzy_results = _resolve_suggestions(fuzzy_candidates, ruleset)
    matches.extend(fuzzy_results)
    for item in fuzzy_results:
        pending_left.add(item.transaction_ids[0])
        pending_right.add(item.transaction_ids[1])

    # Pass 4: only caller-supplied aggregate candidate groups are evaluated.
    reserved_aggregate_ids: set[str] = set()

    for group in aggregate_candidates:
        if not group.left_transaction_ids or not group.right_transaction_ids:
            raise ValueError("Aggregate candidate groups cannot be empty.")
        if len(set(group.left_transaction_ids)) != len(group.left_transaction_ids):
            raise ValueError("Aggregate candidate contains duplicate left IDs.")
        if len(set(group.right_transaction_ids)) != len(group.right_transaction_ids):
            raise ValueError("Aggregate candidate contains duplicate right IDs.")
        if not set(group.left_transaction_ids).issubset(left_by_id):
            raise ValueError("Aggregate candidate contains unknown left IDs.")
        if not set(group.right_transaction_ids).issubset(right_by_id):
            raise ValueError("Aggregate candidate contains unknown right IDs.")

        left_ids = set(group.left_transaction_ids)
        right_ids = set(group.right_transaction_ids)

        if left_ids & consumed_left or right_ids & consumed_right:
            raise ValueError("Aggregate candidate overlaps a confirmed match.")
        if left_ids & pending_left or right_ids & pending_right:
            raise ValueError(
                "Aggregate candidate overlaps a pending review candidate."
            )
        if (left_ids | right_ids) & reserved_aggregate_ids:
            raise ValueError("Aggregate candidate groups overlap.")

        result = match_aggregate_group(
            [left_by_id[item] for item in group.left_transaction_ids],
            [right_by_id[item] for item in group.right_transaction_ids],
            ruleset,
        )
        aggregate_results.append(result)

        if result.outcome in {MatchOutcome.SUGGESTED, MatchOutcome.AMBIGUOUS}:
            pending_left.update(left_ids)
            pending_right.update(right_ids)
            reserved_aggregate_ids.update(left_ids | right_ids)

    # Duplicate evidence is source-local. Rows involved in duplicate evidence
    # must not remain silently auto-confirmed.
    duplicate_evidence = (
        detect_duplicates(left_transactions)
        + detect_duplicates(right_transactions)
    )
    duplicate_left_ids = {
        transaction_id
        for evidence in duplicate_evidence
        if evidence.source_type == left_source
        for transaction_id in evidence.transaction_ids
    }
    duplicate_right_ids = {
        transaction_id
        for evidence in duplicate_evidence
        if evidence.source_type == right_source
        for transaction_id in evidence.transaction_ids
    }

    adjusted_matches = []
    for item in matches:
        left_id, right_id = item.transaction_ids
        if left_id in duplicate_left_ids or right_id in duplicate_right_ids:
            if item.outcome == MatchOutcome.CONFIRMED_AUTO:
                item = MatchingResult(
                    outcome=MatchOutcome.AMBIGUOUS,
                    rule_id=item.rule_id,
                    transaction_ids=item.transaction_ids,
                    evidence=item.evidence,
                    candidate_score=item.candidate_score,
                    ruleset_version=ruleset.version,
                    ruleset_hash=ruleset.fingerprint,
                )
            pending_left.add(left_id)
            pending_right.add(right_id)
        adjusted_matches.append(item)
    matches = adjusted_matches

    outcomes: dict[str, MatchOutcome] = {}

    for item in matches:
        left_id, right_id = item.transaction_ids
        if item.outcome == MatchOutcome.CONFIRMED_AUTO:
            outcomes[transaction_key(left_by_id[left_id])] = MatchOutcome.CONFIRMED_AUTO
            outcomes[transaction_key(right_by_id[right_id])] = MatchOutcome.CONFIRMED_AUTO
        else:
            for transaction in (left_by_id[left_id], right_by_id[right_id]):
                key = transaction_key(transaction)
                existing = outcomes.get(key)
                if existing is None:
                    outcomes[key] = item.outcome
                elif existing != MatchOutcome.CONFIRMED_AUTO:
                    outcomes[key] = MatchOutcome.AMBIGUOUS

    for item in aggregate_results:
        for transaction_id in item.transaction_ids:
            transaction = (
                left_by_id[transaction_id]
                if transaction_id in left_by_id
                else right_by_id[transaction_id]
            )
            key = transaction_key(transaction)
            if key not in outcomes:
                outcomes[key] = item.outcome
            elif outcomes[key] != MatchOutcome.CONFIRMED_AUTO:
                outcomes[key] = MatchOutcome.AMBIGUOUS

    # Duplicate rows not already represented by a match are pending review.
    for transaction in left_transactions:
        if transaction.transaction_id in duplicate_left_ids:
            outcomes[transaction_key(transaction)] = MatchOutcome.AMBIGUOUS
    for transaction in right_transactions:
        if transaction.transaction_id in duplicate_right_ids:
            outcomes[transaction_key(transaction)] = MatchOutcome.AMBIGUOUS

    # Residual rows are those not matched, suggested, ambiguous, or duplicate.
    residual_left = tuple(
        item for item in left_transactions
        if transaction_key(item) not in outcomes
    )
    residual_right = tuple(
        item for item in right_transactions
        if transaction_key(item) not in outcomes
    )

    # Discrepancies require a unique normalized-reference relationship.
    left_by_reference: dict[str, list[MatchingTransaction]] = defaultdict(list)
    right_by_reference: dict[str, list[MatchingTransaction]] = defaultdict(list)

    for item in residual_left:
        reference = (item.reference_norm or item.transaction_reference or "").strip().upper()
        if reference:
            left_by_reference[reference].append(item)
    for item in residual_right:
        reference = (item.reference_norm or item.transaction_reference or "").strip().upper()
        if reference:
            right_by_reference[reference].append(item)

    discrepancy_findings = []
    for reference in sorted(set(left_by_reference) & set(right_by_reference)):
        left_candidates = left_by_reference[reference]
        right_candidates = right_by_reference[reference]
        if len(left_candidates) != 1 or len(right_candidates) != 1:
            continue

        left = left_candidates[0]
        right = right_candidates[0]
        findings = detect_discrepancies(
            DiscrepancyInput(left=left, right=right),
            ruleset,
        )
        if findings:
            discrepancy_findings.extend(findings)
            outcomes[transaction_key(left)] = MatchOutcome.AMBIGUOUS
            outcomes[transaction_key(right)] = MatchOutcome.AMBIGUOUS

    exceptions = classify_discrepancies(discrepancy_findings)

    # Only records without a defensible candidate relationship are classified
    # as missing from the opposite source.
    missing_left = tuple(
        item for item in left_transactions
        if transaction_key(item) not in outcomes
    )
    missing_right = tuple(
        item for item in right_transactions
        if transaction_key(item) not in outcomes
    )

    missing_evidence = detect_missing_transactions(
        missing_left,
        missing_right,
        expected_left_source=left_source,
        expected_right_source=right_source,
    )

    for transaction in missing_left + missing_right:
        outcomes[transaction_key(transaction)] = MatchOutcome.UNMATCHED

    status = calculate_track_status(
        track_name=track_name,
        left_transactions=left_transactions,
        right_transactions=right_transactions,
        outcomes=outcomes,
    )

    pending_ids = {
        transaction_id
        for transaction_id in pending_left | pending_right
    }
    pending_ids.update(
        item.transaction_id
        for item in left_transactions + right_transactions
        if outcomes[transaction_key(item)] == MatchOutcome.AMBIGUOUS
    )

    return TrackResult(
        track_name=track_name,
        source_type=left_source,
        matches=tuple(matches),
        aggregate_results=tuple(aggregate_results),
        duplicate_evidence=tuple(duplicate_evidence),
        missing_evidence=missing_evidence,
        exceptions=exceptions,
        outcomes=dict(sorted(outcomes.items())),
        status=status,
        pending_transaction_ids=tuple(sorted(pending_ids)),
        ruleset_version=ruleset.version,
        ruleset_hash=ruleset.fingerprint,
    )


def run_reconciliation(
    *,
    bank_transactions: Iterable[MatchingTransaction],
    ledger_transactions: Iterable[MatchingTransaction],
    gateway_transactions: Iterable[MatchingTransaction],
    ruleset: MatchingRuleset,
    bank_aggregate_candidates: Iterable[AggregateCandidateGroup] = (),
    gateway_aggregate_candidates: Iterable[AggregateCandidateGroup] = (),
) -> ReconciliationResult:
    """Run independent Bank–Ledger and Gateway–Ledger reconciliation tracks."""

    bank = tuple(bank_transactions)
    ledger = tuple(ledger_transactions)
    gateway = tuple(gateway_transactions)

    _validate_source_collection(bank, SourceType.BANK, "Bank collection")
    _validate_source_collection(ledger, SourceType.LEDGER, "Ledger collection")
    _validate_source_collection(gateway, SourceType.GATEWAY, "Gateway collection")

    bank_track = _build_track(
        track_name="BANK_LEDGER",
        left_transactions=bank,
        right_transactions=ledger,
        left_source=SourceType.BANK,
        right_source=SourceType.LEDGER,
        ruleset=ruleset,
        aggregate_candidates=tuple(bank_aggregate_candidates),
    )

    gateway_track = _build_track(
        track_name="GATEWAY_LEDGER",
        left_transactions=gateway,
        right_transactions=ledger,
        left_source=SourceType.GATEWAY,
        right_source=SourceType.LEDGER,
        ruleset=ruleset,
        aggregate_candidates=tuple(gateway_aggregate_candidates),
    )

    consolidated = calculate_consolidated_status(
        bank_transactions=bank,
        ledger_transactions=ledger,
        gateway_transactions=gateway,
        track_statuses={
            "BANK_LEDGER": bank_track.status,
            "GATEWAY_LEDGER": gateway_track.status,
        },
    )

    return ReconciliationResult(
        bank_ledger=bank_track,
        gateway_ledger=gateway_track,
        consolidated_status=consolidated,
        ruleset_version=ruleset.version,
        ruleset_hash=ruleset.fingerprint,
    )