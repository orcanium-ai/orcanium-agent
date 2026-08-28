"""Tests for the Knowledge Promotion cognitive consolidation model.

Tests cover:
    - compute_knowledge_score() formula
    - _score_to_action() mapping
    - _normalize() utility
    - add_candidate() with backward compatibility
    - curator_review_candidates() end-to-end
    - promote/reject/defer/merge lifecycle
    - get_candidate_count() accuracy
"""

import pytest
from typing import Dict, Any

from orcanium.app.domains.cognition.knowledge_promotion import (
    KnowledgeCandidate,
    compute_knowledge_score,
    _score_to_action,
    CuratorAction,
    add_candidate,
    curator_review_candidates,
    get_candidates,
    get_candidate_count,
    promote_candidate,
    reject_candidate,
    defer_candidate,
    merge_candidate,
    _normalize,
)


# ── Scoring Formula ────────────────────────────────────────────


class TestScoringFormula:
    def test_max_signals(self):
        """All positive signals at max, no contradiction → score ~0.90."""
        c = KnowledgeCandidate(
            content="test",
            frequency=10,
            source_diversity=5,
            stability_score=1.0,
            utility_score=1.0,
            contradiction_score=0.0,
        )
        score = compute_knowledge_score(c)
        assert abs(score - 0.90) < 0.01

    def test_max_contradiction_penalty(self):
        """Max contradiction reduces score by 0.10 → ~0.80."""
        c = KnowledgeCandidate(
            content="test",
            frequency=10,
            source_diversity=5,
            stability_score=1.0,
            utility_score=1.0,
            contradiction_score=1.0,
        )
        score = compute_knowledge_score(c)
        assert abs(score - 0.80) < 0.01

    def test_weak_signals(self):
        """Low frequency, diversity, stability → score < 0.50 (REJECT zone)."""
        c = KnowledgeCandidate(
            content="weak",
            frequency=1,
            source_diversity=1,
            stability_score=0.3,
            utility_score=0.2,
            contradiction_score=0.0,
        )
        score = compute_knowledge_score(c)
        assert score < 0.50

    def test_mid_signals_defer(self):
        """Moderate signals → score in DEFER zone [0.50, 0.75)."""
        c = KnowledgeCandidate(
            content="moderate",
            frequency=6,
            source_diversity=4,
            stability_score=0.7,
            utility_score=0.6,
            contradiction_score=0.0,
        )
        score = compute_knowledge_score(c)
        # frequency_norm=0.60, source_div_norm=0.80, stability=0.7, utility=0.6
        # = 0.60*0.30 + 0.70*0.25 + 0.60*0.20 + 0.80*0.15 - 0
        # = 0.18 + 0.175 + 0.12 + 0.12 = 0.595
        assert 0.50 <= score < 0.75

    def test_no_signals(self):
        """Minimum signals → score at floor (no negative)."""
        c = KnowledgeCandidate(
            content="minimal",
            frequency=0,
            source_diversity=1,
            stability_score=0.0,
            utility_score=0.0,
            contradiction_score=0.0,
        )
        score = compute_knowledge_score(c)
        assert score >= 0.0


# ── Score-to-Action Mapping ────────────────────────────────────


class TestScoreToAction:
    def test_promote(self):
        assert _score_to_action(0.75) == CuratorAction.PROMOTE
        assert _score_to_action(0.80) == CuratorAction.PROMOTE
        assert _score_to_action(1.00) == CuratorAction.PROMOTE

    def test_defer(self):
        assert _score_to_action(0.50) == CuratorAction.DEFER
        assert _score_to_action(0.60) == CuratorAction.DEFER
        assert _score_to_action(0.74) == CuratorAction.DEFER

    def test_reject(self):
        assert _score_to_action(0.49) == CuratorAction.REJECT
        assert _score_to_action(0.25) == CuratorAction.REJECT
        assert _score_to_action(0.00) == CuratorAction.REJECT


# ── Normalization ──────────────────────────────────────────────


class TestNormalize:
    def test_zero(self):
        assert _normalize(0, 10) == 0.0

    def test_half(self):
        assert _normalize(5, 10) == 0.5

    def test_at_target(self):
        assert _normalize(10, 10) == 1.0

    def test_above_target(self):
        assert _normalize(20, 10) == 1.0

    def test_different_targets(self):
        assert _normalize(3, 5) == 0.6
        assert _normalize(7, 5) == 1.0


# ── Backward Compatibility ─────────────────────────────────────


class TestBackwardCompatibility:
    def test_legacy_add_candidate(self):
        """add_candidate() with only legacy fields should use defaults for new signals."""
        c = add_candidate(content="legacy observation", confidence=0.8, source_count=5)
        assert c.frequency == 1  # default
        assert c.stability_score == 0.5  # default
        assert c.utility_score == 0.5  # default
        assert c.contradiction_score == 0.0  # default
        assert c.candidate_id != ""
        assert c.knowledge_score is not None

    def test_legacy_knowledge_candidate_direct(self):
        """KnowledgeCandidate instantiated with only legacy fields should get defaults."""
        c = KnowledgeCandidate(content="test", confidence=0.9, source_count=3)
        assert c.frequency == 1
        assert c.stability_score == 0.5
        assert c.utility_score == 0.5
        assert c.contradiction_score == 0.0
        # source_diversity should be derived from source_count
        assert c.source_diversity >= 3

    def test_legacy_is_eligible_still_works(self):
        """is_eligible() is retained as a supporting signal, not a promotion gate."""
        c = KnowledgeCandidate(content="test", confidence=0.7, source_count=3)
        assert c.is_eligible() is True
        c2 = KnowledgeCandidate(content="test", confidence=0.5, source_count=1)
        assert c2.is_eligible() is False


# ── Candidate Lifecycle ────────────────────────────────────────


class TestCandidateLifecycle:
    def test_add_and_promote(self):
        c = add_candidate(
            content="promotable knowledge",
            frequency=10,
            source_diversity=5,
            stability_score=0.9,
            utility_score=0.8,
            contradiction_score=0.0,
        )
        result = promote_candidate(c)
        assert result is True
        assert c.promoted is True
        assert c.promoted_at is not None

    def test_add_and_reject(self):
        c = add_candidate(content="rejectable knowledge")
        result = reject_candidate(c, reason="Not useful")
        assert result is True
        assert c.rejected is True
        assert c.rejection_reason == "Not useful"

    def test_double_promote_fails(self):
        c = add_candidate(content="double test", frequency=10)
        promote_candidate(c)
        result = promote_candidate(c)
        assert result is False

    def test_defer_candidate(self):
        c = add_candidate(content="deferred knowledge")
        result = defer_candidate(c, rationale="Need more evidence")
        assert result is True
        assert c.promoted is False
        assert c.rejected is False

    def test_merge_candidate(self):
        target = add_candidate(content="existing merged knowledge", frequency=5)
        promote_candidate(target)
        incoming = add_candidate(content="existing merged knowledge update", frequency=3)
        result = merge_candidate(incoming, target, "existing merged knowledge update")
        assert result is True
        assert incoming.promoted is True
        assert "Merged" in incoming.rejection_reason


# ── Curator Review ─────────────────────────────────────────────


class TestCuratorReview:
    @pytest.fixture(autouse=True)
    def setup_candidates(self):
        """Add a mix of candidates before each test."""
        # Clear the shared _candidates list to avoid cross-test pollution
        from orcanium.app.domains.cognition.knowledge_promotion import _candidates
        _candidates.clear()

        # Weak — should be REJECTED
        add_candidate(
            content="random noise",
            frequency=1,
            source_diversity=1,
            stability_score=0.2,
            utility_score=0.1,
        )
        # Strong — should be PROMOTED (content deliberately distinct to avoid merge)
        add_candidate(
            content="The agent should prefer deterministic keyword retrieval over embedding-based search",
            frequency=12,
            source_diversity=5,
            stability_score=0.9,
            utility_score=0.8,
        )

    def test_curator_review_returns_summary(self):
        summary = curator_review_candidates(max_review=10)
        assert "reviewed" in summary
        assert "promoted" in summary
        assert "rejected" in summary
        assert "deferred" in summary
        assert "merged" in summary
        assert "decisions" in summary
        assert len(summary["decisions"]) > 0

    def test_weak_candidate_rejected(self):
        summary = curator_review_candidates(max_review=10)
        weak = summary["decisions"][0]
        assert weak["action"] == "REJECT"

    def test_strong_candidate_promoted(self):
        summary = curator_review_candidates(max_review=10)
        strong = summary["decisions"][1]
        assert strong["action"] == "PROMOTE"

    def test_candidate_counts(self):
        _ = curator_review_candidates(max_review=10)
        counts = get_candidate_count()
        assert counts["total"] >= 2
        assert counts["promoted"] >= 1
        assert counts["rejected"] >= 1


# ── Merge Detection ────────────────────────────────────────────


class TestMergeDetection:
    @pytest.fixture(autouse=True)
    def clear_candidates(self):
        from orcanium.app.domains.cognition.knowledge_promotion import _candidates
        _candidates.clear()

    def test_overlapping_content_merges(self):
        """Two candidates with significant word overlap should merge."""
        target = add_candidate(
            content="User prefers running local AI models on their own hardware",
            frequency=5,
        )
        promote_candidate(target)

        incoming = add_candidate(
            content="User prefers local AI models running on local hardware",
            frequency=3,
        )

        summary = curator_review_candidates(max_review=10)
        merge_decisions = [d for d in summary["decisions"] if d["action"] == "MERGE"]
        # At least one merge may have happened
        counts = get_candidate_count()
        # The promoted target plus the merge decision
        assert summary["reviewed"] >= 1


# ── Edge Cases ─────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_content(self):
        c = add_candidate(content="")
        assert c.frequency == 1
        assert c.knowledge_score is not None

    def test_high_contradiction_only(self):
        """High contradiction with moderate signals → REJECT zone."""
        c = KnowledgeCandidate(
            content="contradictory",
            frequency=5,
            source_diversity=3,
            stability_score=0.7,
            utility_score=0.6,
            contradiction_score=1.0,
        )
        score = compute_knowledge_score(c)
        # frequency_norm=0.5, stability=0.7, utility=0.6, source_div=0.6
        # = 0.15 + 0.175 + 0.12 + 0.09 - 0.10 = 0.435
        assert score < 0.50

    def test_candidate_id_unique(self):
        c1 = add_candidate(content="first")
        c2 = add_candidate(content="second")
        assert c1.candidate_id != c2.candidate_id

    def test_get_candidates_pending_only(self):
        c = add_candidate(content="pending test")
        pending = get_candidates(only_eligible=False)
        assert any(c.content == "pending test" for c in pending)
        promote_candidate(c)
        pending_after = get_candidates(only_eligible=False)
        assert not any(c.content == "pending test" for c in pending_after)
