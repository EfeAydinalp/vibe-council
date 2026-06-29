"""Tests for provider-aware usage/cost messaging (v0.2 PR 6).

Stdlib-only (`unittest`), no provider calls. Verify that:
- OpenRouter cost reporting/enforcement is unchanged when a cost is present,
- providers that don't report cost (e.g. Ollama) say so explicitly,
- no fabricated $0.00 cost is produced,
- `--max-cost` never implies enforcement when cost is missing,
- token estimation is unaffected.
"""

import unittest

from backend import guards


def _summary_with_cost(cost):
    return {"totals": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "has_tokens": True, "reported_cost": cost}


def _summary_no_cost():
    return {"totals": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "has_tokens": True}


class TestCostNote(unittest.TestCase):
    def test_openrouter_reported_cost_unchanged(self):
        note = guards.cost_note(_summary_with_cost(0.0123), "openrouter")
        self.assertEqual(note, "Provider-reported cost: $0.0123 (as reported by OpenRouter).")

    def test_openrouter_no_cost_is_silent(self):
        # Unchanged behavior: OpenRouter without cost data prints no cost line.
        self.assertIsNone(guards.cost_note(_summary_no_cost(), "openrouter"))

    def test_ollama_no_cost_says_not_reported(self):
        note = guards.cost_note(_summary_no_cost(), "ollama")
        self.assertIn("not reported by provider 'ollama'", note)
        self.assertNotIn("$0.00", note)
        self.assertNotIn("$0", note)

    def test_other_provider_reported_cost_is_provider_labeled(self):
        note = guards.cost_note(_summary_with_cost(0.5), "ollama")
        self.assertIn("(as reported by provider 'ollama')", note)

    def test_default_provider_is_openrouter(self):
        # Back-compat: default arg keeps the historical OpenRouter wording.
        self.assertEqual(guards.cost_note(_summary_with_cost(1.0)),
                         "Provider-reported cost: $1.0 (as reported by OpenRouter).")


class TestEnforceCostCap(unittest.TestCase):
    def test_no_max_cost_is_noop(self):
        exceeded, reported, msg = guards.enforce_cost_cap(_summary_with_cost(9.9), None, "ollama")
        self.assertFalse(exceeded)
        self.assertIsNone(msg)

    def test_openrouter_within_cap(self):
        exceeded, reported, msg = guards.enforce_cost_cap(_summary_with_cost(0.10), 0.20, "openrouter")
        self.assertFalse(exceeded)
        self.assertEqual(reported, 0.10)
        self.assertIn("within --max-cost", msg)

    def test_openrouter_exceeds_cap(self):
        exceeded, reported, msg = guards.enforce_cost_cap(_summary_with_cost(0.50), 0.20, "openrouter")
        self.assertTrue(exceeded)
        self.assertIn("exceeds --max-cost", msg)

    def test_ollama_missing_cost_not_enforced_and_not_exceeded(self):
        exceeded, reported, msg = guards.enforce_cost_cap(_summary_no_cost(), 0.20, "ollama")
        self.assertFalse(exceeded)          # never fails just because cost is missing
        self.assertIsNone(reported)         # no fabricated dollar figure
        self.assertIn("could not be enforced", msg)
        self.assertIn("provider 'ollama' did not report cost", msg)

    def test_openrouter_missing_cost_names_openrouter(self):
        exceeded, reported, msg = guards.enforce_cost_cap(_summary_no_cost(), 0.20, "openrouter")
        self.assertFalse(exceeded)
        self.assertIn("provider 'openrouter' did not report cost", msg)


class TestNoFakeCostInAggregate(unittest.TestCase):
    def test_ollama_style_usage_has_no_reported_cost(self):
        # Ollama usage carries token-ish stats but no `cost` key.
        items = [{"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18,
                  "total_duration": 12345}]
        summary = guards.aggregate_usage(items)
        self.assertTrue(summary["has_tokens"])
        self.assertNotIn("reported_cost", summary)  # no fabricated $0.00


class TestTokenGuardUnchanged(unittest.TestCase):
    def test_token_estimate_still_works(self):
        ok, est, msg = guards.token_guard("hello world " * 50, "review", 3, None)
        self.assertTrue(ok)
        self.assertGreater(est, 0)
        ok2, est2, msg2 = guards.token_guard("x" * 10000, "review", 3, 1)
        self.assertFalse(ok2)  # exceeds --max-tokens, unchanged behavior


if __name__ == "__main__":
    unittest.main()
