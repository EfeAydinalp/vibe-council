"""Regression tests for `full`-mode ranking robustness.

Stdlib-only (`unittest`), no model calls. These cover the historically fragile
path where a ranking model returns `None` / empty / whitespace-only / unparsable
content and the parser or aggregation step crashes (TypeError on `None`).

The contract: empty/missing/unparsable ranking text yields "no ranking parsed"
(an empty list) rather than raising, while valid ranking text still parses.
"""

import unittest

from backend.council import parse_ranking_from_text, calculate_aggregate_rankings


VALID_RANKING = (
    "Response A is thorough but slow...\n"
    "Response B is concise...\n\n"
    "FINAL RANKING:\n"
    "1. Response B\n"
    "2. Response A\n"
)


class TestParseRankingToleratesBadInput(unittest.TestCase):
    def test_none_does_not_crash(self):
        self.assertEqual(parse_ranking_from_text(None), [])

    def test_empty_string_does_not_crash(self):
        self.assertEqual(parse_ranking_from_text(""), [])

    def test_whitespace_only_does_not_crash(self):
        self.assertEqual(parse_ranking_from_text("   \n\t  "), [])

    def test_unparsable_text_returns_empty(self):
        self.assertEqual(parse_ranking_from_text("no ranking section at all here"), [])

    def test_final_ranking_header_without_labels(self):
        # Header present but no "Response X" labels follow.
        self.assertEqual(parse_ranking_from_text("FINAL RANKING:\n(none provided)"), [])


class TestParseRankingValidStillWorks(unittest.TestCase):
    def test_numbered_final_ranking_order_preserved(self):
        self.assertEqual(parse_ranking_from_text(VALID_RANKING), ["Response B", "Response A"])

    def test_labels_without_header_fallback(self):
        # No "FINAL RANKING:" header -> fall back to any "Response X" mentions.
        self.assertEqual(
            parse_ranking_from_text("I prefer Response C then Response A."),
            ["Response C", "Response A"],
        )


class TestAggregateRankingsToleratesEmptyRanker(unittest.TestCase):
    def test_one_empty_ranking_is_skipped_not_crashed(self):
        label_to_model = {"Response A": "model-a", "Response B": "model-b"}
        stage2_results = [
            {"model": "ranker-1", "ranking": VALID_RANKING},   # valid
            {"model": "ranker-2", "ranking": None},            # empty content
            {"model": "ranker-3", "ranking": ""},              # empty string
            {"model": "ranker-4", "ranking": "   "},           # whitespace only
        ]
        # Must not raise, and must still aggregate the one valid ranking.
        aggregate = calculate_aggregate_rankings(stage2_results, label_to_model)
        models = {row["model"] for row in aggregate}
        self.assertEqual(models, {"model-a", "model-b"})
        ranks = {row["model"]: row["average_rank"] for row in aggregate}
        # VALID_RANKING ranks B (pos 1) above A (pos 2).
        self.assertLess(ranks["model-b"], ranks["model-a"])

    def test_all_empty_rankings_yield_empty_aggregate(self):
        label_to_model = {"Response A": "model-a"}
        stage2_results = [
            {"model": "ranker-1", "ranking": None},
            {"model": "ranker-2", "ranking": ""},
        ]
        self.assertEqual(calculate_aggregate_rankings(stage2_results, label_to_model), [])


if __name__ == "__main__":
    unittest.main()
