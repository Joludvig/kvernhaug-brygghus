"""
Tests for bryggeskole/mastery.py -- the hidden per-concept mastery state
model (V2-3B, issue #97).

Pure module, no file I/O -- see tests/test_bryggeskole_mastery_store.py
for the separate persistence-layer tests.

Run with:
    python3 -m unittest tests.test_bryggeskole_mastery
"""
import unittest

from bryggeskole.mastery import (
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    MASTERY_GAIN_FIRST_ATTEMPT,
    MASTERY_GAIN_RECOVERY,
    MASTERY_MAX,
    MASTERY_MIN,
    MASTERY_STATE_SCHEMA_VERSION,
    apply_answer,
    mastery_label,
    neutral_concept_state,
    update_concept_state,
    validate_mastery_state,
)

_NOW = "2026-09-06T12:00:00+00:00"
_LATER = "2026-09-06T13:00:00+00:00"

_QUESTION = {
    "id": "Q-FERM-001",
    "concepts": ["fermentation.temperature", "fermentation.yeast_activity"],
}


class TestNeutralConceptState(unittest.TestCase):
    def test_neutral_baseline_values(self):
        state = neutral_concept_state()
        self.assertEqual(state["mastery"], 0.0)
        self.assertEqual(state["confidence"], 0.0)
        self.assertEqual(state["attempts"], 0)
        self.assertIsNone(state["last_tested"])


class TestUpdateConceptStateRequiredBehavior(unittest.TestCase):
    def test_correct_first_attempt_increases_mastery_and_confidence(self):
        updated = update_concept_state(None, correct=True, first_attempt=True, now=_NOW)
        self.assertGreater(updated["mastery"], 0.0)
        self.assertGreater(updated["confidence"], 0.0)

    def test_incorrect_answer_never_increases_mastery(self):
        previous = update_concept_state(None, correct=True, first_attempt=True, now=_NOW)
        after_miss = update_concept_state(previous, correct=False, first_attempt=False, now=_LATER)
        self.assertLessEqual(after_miss["mastery"], previous["mastery"])

    def test_incorrect_answer_from_neutral_state_keeps_mastery_at_zero(self):
        updated = update_concept_state(None, correct=False, first_attempt=True, now=_NOW)
        self.assertEqual(updated["mastery"], 0.0)

    def test_recovery_after_miss_increases_mastery_less_than_first_attempt(self):
        first_attempt_correct = update_concept_state(None, correct=True, first_attempt=True, now=_NOW)
        recovery_correct = update_concept_state(None, correct=True, first_attempt=False, now=_NOW)
        self.assertGreater(first_attempt_correct["mastery"], recovery_correct["mastery"])
        self.assertGreater(recovery_correct["mastery"], 0.0)

    def test_recovery_gain_constant_is_smaller_than_first_attempt_gain(self):
        self.assertLess(MASTERY_GAIN_RECOVERY, MASTERY_GAIN_FIRST_ATTEMPT)

    def test_attempts_increments_by_exactly_one(self):
        state = neutral_concept_state()
        for expected in (1, 2, 3):
            state = update_concept_state(state, correct=True, first_attempt=(expected == 1), now=_NOW)
            self.assertEqual(state["attempts"], expected)

    def test_last_tested_updates_to_supplied_timestamp(self):
        updated = update_concept_state(None, correct=True, first_attempt=True, now=_NOW)
        self.assertEqual(updated["last_tested"], _NOW)
        updated_again = update_concept_state(updated, correct=True, first_attempt=False, now=_LATER)
        self.assertEqual(updated_again["last_tested"], _LATER)

    def test_mastery_and_confidence_remain_bounded_after_many_correct_answers(self):
        state = neutral_concept_state()
        for _ in range(50):
            state = update_concept_state(state, correct=True, first_attempt=False, now=_NOW)
        self.assertLessEqual(state["mastery"], MASTERY_MAX)
        self.assertLessEqual(state["confidence"], CONFIDENCE_MAX)

    def test_confidence_remains_bounded_after_many_incorrect_answers(self):
        state = update_concept_state(None, correct=True, first_attempt=True, now=_NOW)
        for _ in range(50):
            state = update_concept_state(state, correct=False, first_attempt=False, now=_NOW)
        self.assertGreaterEqual(state["confidence"], CONFIDENCE_MIN)
        self.assertGreaterEqual(state["mastery"], MASTERY_MIN)

    def test_unknown_concept_created_safely_from_neutral_baseline(self):
        updated = update_concept_state(None, correct=True, first_attempt=True, now=_NOW)
        expected_from_explicit_baseline = update_concept_state(
            neutral_concept_state(), correct=True, first_attempt=True, now=_NOW
        )
        self.assertEqual(updated, expected_from_explicit_baseline)

    def test_rejects_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            update_concept_state(None, correct=True, first_attempt=True, now="not-a-timestamp")

    def test_is_pure_does_not_mutate_previous(self):
        previous = update_concept_state(None, correct=True, first_attempt=True, now=_NOW)
        snapshot = dict(previous)
        update_concept_state(previous, correct=True, first_attempt=False, now=_LATER)
        self.assertEqual(previous, snapshot)


class TestApplyAnswerUpdatesEveryDeclaredConcept(unittest.TestCase):
    def test_updates_all_concepts_referenced_by_question(self):
        document = {"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": {}, "answered_questions": {}}
        updated = apply_answer(document, _QUESTION, correct=True, now=_NOW)
        for concept_id in _QUESTION["concepts"]:
            self.assertIn(concept_id, updated["concepts"])
            self.assertGreater(updated["concepts"][concept_id]["mastery"], 0.0)

    def test_does_not_mutate_input_document(self):
        document = {"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": {}, "answered_questions": {}}
        apply_answer(document, _QUESTION, correct=True, now=_NOW)
        self.assertEqual(document["concepts"], {})
        self.assertEqual(document["answered_questions"], {})

    def test_second_answer_to_same_question_is_not_first_attempt(self):
        document = {"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": {}, "answered_questions": {}}
        after_first_miss = apply_answer(document, _QUESTION, correct=False, now=_NOW)
        after_recovery = apply_answer(after_first_miss, _QUESTION, correct=True, now=_LATER)

        first_attempt_only = apply_answer(document, _QUESTION, correct=True, now=_NOW)

        concept_id = _QUESTION["concepts"][0]
        self.assertLess(
            after_recovery["concepts"][concept_id]["mastery"],
            first_attempt_only["concepts"][concept_id]["mastery"],
        )

    def test_tracks_answered_question_attempts_and_last_correct(self):
        document = {"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": {}, "answered_questions": {}}
        after_first = apply_answer(document, _QUESTION, correct=False, now=_NOW)
        entry = after_first["answered_questions"][_QUESTION["id"]]
        self.assertEqual(entry["attempts"], 1)
        self.assertFalse(entry["last_correct"])
        self.assertEqual(entry["last_tested"], _NOW)

        after_second = apply_answer(after_first, _QUESTION, correct=True, now=_LATER)
        entry_2 = after_second["answered_questions"][_QUESTION["id"]]
        self.assertEqual(entry_2["attempts"], 2)
        self.assertTrue(entry_2["last_correct"])
        self.assertEqual(entry_2["last_tested"], _LATER)

    def test_rejects_question_with_no_concepts(self):
        document = {"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": {}, "answered_questions": {}}
        with self.assertRaises(ValueError):
            apply_answer(document, {"id": "Q-X-001", "concepts": []}, correct=True, now=_NOW)


class TestMasteryLabelIsDeterministicAndNeverRaw(unittest.TestCase):
    def test_high_mastery_maps_to_strong_area(self):
        state = {"mastery": 0.9, "confidence": 0.9, "attempts": 5, "last_tested": _NOW}
        self.assertEqual(mastery_label(state, "en"), "Strong area")
        self.assertEqual(mastery_label(state, "no"), "Sterkt område")

    def test_zero_mastery_maps_to_should_repeat(self):
        state = neutral_concept_state()
        self.assertEqual(mastery_label(state, "en"), "Should repeat")
        self.assertEqual(mastery_label(state, "no"), "Bør repeteres")

    def test_thresholds_are_monotonic_and_deterministic(self):
        samples = [0.0, 0.1, 0.24, 0.25, 0.49, 0.5, 0.74, 0.75, 0.99, 1.0]
        for mastery in samples:
            state = {"mastery": mastery, "confidence": 0.0, "attempts": 1, "last_tested": _NOW}
            label_1 = mastery_label(state, "en")
            label_2 = mastery_label(state, "en")
            self.assertEqual(label_1, label_2)

    def test_rejects_unsupported_language(self):
        state = neutral_concept_state()
        with self.assertRaises(ValueError):
            mastery_label(state, "de")

    def test_no_raw_score_or_grade_in_any_label(self):
        from bryggeskole.mastery import LABEL_FALLBACK, LABEL_THRESHOLDS

        all_labels = [LABEL_FALLBACK["no"], LABEL_FALLBACK["en"]]
        for _, labels in LABEL_THRESHOLDS:
            all_labels.extend([labels["no"], labels["en"]])
        for label in all_labels:
            self.assertNotIn("/", label)
            self.assertFalse(any(char.isdigit() for char in label))


class TestValidateMasteryStateMalformedTopLevel(unittest.TestCase):
    def test_non_dict_document_fails(self):
        errors = validate_mastery_state(["not", "a", "dict"])
        self.assertTrue(errors)

    def test_unknown_top_level_field_fails(self):
        document = {
            "schema_version": MASTERY_STATE_SCHEMA_VERSION,
            "concepts": {},
            "unexpected_field": True,
        }
        errors = validate_mastery_state(document)
        self.assertTrue(any("unexpected_field" in e for e in errors))

    def test_wrong_schema_version_fails(self):
        document = {"schema_version": 999, "concepts": {}}
        errors = validate_mastery_state(document)
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_concepts_must_be_an_object(self):
        document = {"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": ["not", "a", "dict"]}
        errors = validate_mastery_state(document)
        self.assertTrue(any("'concepts'" in e for e in errors))

    def test_minimal_valid_document_has_no_errors(self):
        document = {"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": {}}
        self.assertEqual(validate_mastery_state(document), [])

    def test_answered_questions_is_optional(self):
        document = {"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": {}}
        self.assertNotIn("answered_questions", document)
        self.assertEqual(validate_mastery_state(document), [])

    def test_answered_questions_must_be_an_object_when_present(self):
        document = {
            "schema_version": MASTERY_STATE_SCHEMA_VERSION,
            "concepts": {},
            "answered_questions": ["not", "a", "dict"],
        }
        errors = validate_mastery_state(document)
        self.assertTrue(any("'answered_questions'" in e for e in errors))


class TestValidateMasteryStateInvalidConceptEntry(unittest.TestCase):
    def _document(self, concept_entry):
        return {
            "schema_version": MASTERY_STATE_SCHEMA_VERSION,
            "concepts": {"fermentation.temperature": concept_entry},
        }

    def test_valid_entry_passes(self):
        entry = {"mastery": 0.5, "confidence": 0.5, "attempts": 2, "last_tested": _NOW}
        self.assertEqual(validate_mastery_state(self._document(entry)), [])

    def test_entry_must_be_an_object(self):
        errors = validate_mastery_state(self._document("not-a-dict"))
        self.assertTrue(errors)

    def test_missing_required_field_fails(self):
        entry = {"mastery": 0.5, "confidence": 0.5, "attempts": 2}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("last_tested" in e for e in errors))

    def test_unknown_field_fails(self):
        entry = {"mastery": 0.5, "confidence": 0.5, "attempts": 2, "last_tested": _NOW, "extra": 1}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("extra" in e for e in errors))

    def test_negative_attempts_fails(self):
        entry = {"mastery": 0.5, "confidence": 0.5, "attempts": -1, "last_tested": _NOW}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("attempts" in e for e in errors))

    def test_out_of_bound_mastery_fails(self):
        entry = {"mastery": 1.5, "confidence": 0.5, "attempts": 1, "last_tested": _NOW}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("mastery" in e for e in errors))

    def test_out_of_bound_confidence_fails(self):
        entry = {"mastery": 0.5, "confidence": -0.1, "attempts": 1, "last_tested": _NOW}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("confidence" in e for e in errors))

    def test_bad_timestamp_fails(self):
        entry = {"mastery": 0.5, "confidence": 0.5, "attempts": 1, "last_tested": "not-a-timestamp"}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("last_tested" in e for e in errors))

    def test_neutral_untested_concept_with_null_last_tested_passes(self):
        entry = {"mastery": 0.0, "confidence": 0.0, "attempts": 0, "last_tested": None}
        self.assertEqual(validate_mastery_state(self._document(entry)), [])

    def test_zero_attempts_with_non_null_last_tested_fails(self):
        entry = {"mastery": 0.0, "confidence": 0.0, "attempts": 0, "last_tested": _NOW}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("last_tested" in e for e in errors))

    def test_positive_attempts_with_null_last_tested_fails(self):
        entry = {"mastery": 0.5, "confidence": 0.5, "attempts": 1, "last_tested": None}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("last_tested" in e for e in errors))


class TestValidateMasteryStateInvalidQuestionAttemptEntry(unittest.TestCase):
    def _document(self, entry):
        return {
            "schema_version": MASTERY_STATE_SCHEMA_VERSION,
            "concepts": {},
            "answered_questions": {"Q-FERM-001": entry},
        }

    def test_valid_entry_passes(self):
        entry = {"attempts": 1, "last_correct": True, "last_tested": _NOW}
        self.assertEqual(validate_mastery_state(self._document(entry)), [])

    def test_zero_attempts_fails(self):
        entry = {"attempts": 0, "last_correct": True, "last_tested": _NOW}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("attempts" in e for e in errors))

    def test_non_boolean_last_correct_fails(self):
        entry = {"attempts": 1, "last_correct": "yes", "last_tested": _NOW}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("last_correct" in e for e in errors))

    def test_bad_timestamp_fails(self):
        entry = {"attempts": 1, "last_correct": True, "last_tested": "not-a-timestamp"}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("last_tested" in e for e in errors))

    def test_unknown_field_fails(self):
        entry = {"attempts": 1, "last_correct": True, "last_tested": _NOW, "extra": 1}
        errors = validate_mastery_state(self._document(entry))
        self.assertTrue(any("extra" in e for e in errors))

    def test_malformed_entry_type_fails(self):
        errors = validate_mastery_state(self._document("not-a-dict"))
        self.assertTrue(errors)


class TestApplyAnswerProducesValidDocuments(unittest.TestCase):
    def test_result_of_apply_answer_always_validates(self):
        document = {"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": {}, "answered_questions": {}}
        for correct, now in ((False, _NOW), (True, _LATER)):
            document = apply_answer(document, _QUESTION, correct=correct, now=now)
            self.assertEqual(validate_mastery_state(document), [])


if __name__ == "__main__":
    unittest.main()
