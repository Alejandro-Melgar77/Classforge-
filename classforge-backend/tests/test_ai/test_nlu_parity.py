"""
tests/test_ai/test_nlu_parity.py — Cross-platform NLU parity test for Python heuristic engine.

Reads shared fixtures from shared/nlu_cases.json and verifies that Python's
heuristic engine parses all canonical commands with expected action, classes,
and relation semantics.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.modules.ai.heuristic_engine import parse_heuristic
from app.modules.ai.schemas import UMLCommandResponse

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent.parent / "shared" / "nlu_cases.json"

@pytest.fixture(scope="module")
def nlu_cases():
    assert FIXTURES_PATH.exists(), f"Fixtures not found at {FIXTURES_PATH}"
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_fixtures_loaded(nlu_cases):
    assert len(nlu_cases) >= 15

def test_python_nlu_parity_against_shared_fixtures(nlu_cases):
    for case in nlu_cases:
        prompt = case["prompt"]
        accepted_actions = case.get("accepted_actions", [case["expected_action"]])

        result: UMLCommandResponse = parse_heuristic(prompt)
        assert result is not None, f"Failed on prompt: {prompt}"

        # Action alignment
        assert result.action in accepted_actions, (
            f"Action mismatch for '{prompt}': got '{result.action}', expected one of {accepted_actions}"
        )

        # Expected classes
        expected_classes = [c.lower() for c in case.get("expected_classes", [])]
        if expected_classes:
            result_classes = [c.name.lower() for c in result.classes]
            for exp_c in expected_classes:
                assert exp_c in result_classes, (
                    f"Class '{exp_c}' not found in {result_classes} for prompt '{prompt}'"
                )

        # Expected relation type
        if "expected_relation" in case:
            exp_rel = case["expected_relation"]
            assert len(result.relations) >= 1, f"No relations extracted for prompt '{prompt}'"
            rel = result.relations[0]
            assert rel.type.lower() == exp_rel["type"].lower(), (
                f"Relation type mismatch: got {rel.type}, expected {exp_rel['type']}"
            )
            assert rel.source.lower() == exp_rel["source"].lower()
            assert rel.target.lower() == exp_rel["target"].lower()

        # Expected deleted elements
        if "expected_deleted" in case:
            exp_del = [d.lower() for d in case["expected_deleted"]]
            result_del = [d.lower() for d in result.deleted_elements]
            for d in exp_del:
                assert d in result_del, f"Deleted element '{d}' not in {result_del} for '{prompt}'"
