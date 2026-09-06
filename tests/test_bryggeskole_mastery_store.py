"""
Tests for bryggeskole/mastery_store.py -- local JSON persistence for the
hidden per-concept mastery state (V2-3B, issue #97).

Isolation: every test sets KVERNHAUG_BRYGGESKOLE_STATE_DIR to a fresh
tempfile.TemporaryDirectory() in setUp() and restores/removes the env var
in tearDown() -- the same pattern (and reasoning) as
tests/test_pantry.py's isolation of KVERNHAUG_PANTRY_DIR.

Run with:
    python3 -m unittest tests.test_bryggeskole_mastery_store
"""
import json
import os
import tempfile
import unittest

from bryggeskole.mastery import MASTERY_STATE_SCHEMA_VERSION, MasteryStateError, apply_answer
from bryggeskole.mastery_store import (
    _STATE_DIR_ENV,
    default_state_path,
    neutral_state_document,
    read_mastery_state,
    write_mastery_state,
)

_NOW = "2026-09-06T12:00:00+00:00"

_QUESTION = {
    "id": "Q-FERM-001",
    "concepts": ["fermentation.temperature"],
}


class _IsolatedStateDirTestCase(unittest.TestCase):
    def setUp(self):
        self._old_env = os.environ.get(_STATE_DIR_ENV)
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ[_STATE_DIR_ENV] = self._tmpdir.name

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop(_STATE_DIR_ENV, None)
        else:
            os.environ[_STATE_DIR_ENV] = self._old_env
        self._tmpdir.cleanup()


class TestReadMissingFileReturnsNeutralDocument(_IsolatedStateDirTestCase):
    def test_no_file_created_by_reading(self):
        self.assertFalse(os.path.exists(default_state_path()))
        document = read_mastery_state()
        self.assertEqual(document, neutral_state_document())
        self.assertFalse(os.path.exists(default_state_path()))


class TestWriteThenReadRoundTrips(_IsolatedStateDirTestCase):
    def test_round_trip_preserves_document(self):
        document = apply_answer(neutral_state_document(), _QUESTION, correct=True, now=_NOW)
        write_mastery_state(document)
        self.assertTrue(os.path.exists(default_state_path()))
        reloaded = read_mastery_state()
        self.assertEqual(reloaded, document)

    def test_write_uses_atomic_replace_no_leftover_tmp_file(self):
        document = neutral_state_document()
        write_mastery_state(document)
        directory = os.path.dirname(default_state_path())
        leftovers = [f for f in os.listdir(directory) if ".tmp_" in f]
        self.assertEqual(leftovers, [])

    def test_write_creates_state_directory_if_missing(self):
        nested_path = os.path.join(self._tmpdir.name, "nested", "state.json")
        write_mastery_state(neutral_state_document(), path=nested_path)
        self.assertTrue(os.path.exists(nested_path))


class TestWriteNeverPersistsInvalidDocument(_IsolatedStateDirTestCase):
    def test_invalid_document_raises_and_writes_nothing(self):
        invalid_document = {"schema_version": 999, "concepts": {}}
        with self.assertRaises(MasteryStateError):
            write_mastery_state(invalid_document)
        self.assertFalse(os.path.exists(default_state_path()))


class TestReadFailsClosedOnMalformedStoredState(_IsolatedStateDirTestCase):
    def _write_raw(self, content):
        path = default_state_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    def test_invalid_json_raises(self):
        self._write_raw("{not valid json")
        with self.assertRaises(MasteryStateError):
            read_mastery_state()

    def test_malformed_shape_raises(self):
        self._write_raw(json.dumps({"schema_version": MASTERY_STATE_SCHEMA_VERSION, "concepts": "not-a-dict"}))
        with self.assertRaises(MasteryStateError):
            read_mastery_state()

    def test_out_of_bound_mastery_raises(self):
        self._write_raw(
            json.dumps(
                {
                    "schema_version": MASTERY_STATE_SCHEMA_VERSION,
                    "concepts": {
                        "fermentation.temperature": {
                            "mastery": 5.0,
                            "confidence": 0.0,
                            "attempts": 1,
                            "last_tested": _NOW,
                        }
                    },
                }
            )
        )
        with self.assertRaises(MasteryStateError):
            read_mastery_state()

    def test_never_repairs_or_overwrites_malformed_file(self):
        self._write_raw("{not valid json")
        with self.assertRaises(MasteryStateError):
            read_mastery_state()
        with open(default_state_path(), "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "{not valid json")


class TestExplicitPathOverride(_IsolatedStateDirTestCase):
    def test_write_and_read_respect_explicit_path(self):
        explicit_path = os.path.join(self._tmpdir.name, "custom_mastery.json")
        document = apply_answer(neutral_state_document(), _QUESTION, correct=False, now=_NOW)
        write_mastery_state(document, path=explicit_path)
        self.assertTrue(os.path.exists(explicit_path))
        self.assertFalse(os.path.exists(default_state_path()))
        reloaded = read_mastery_state(path=explicit_path)
        self.assertEqual(reloaded, document)


if __name__ == "__main__":
    unittest.main()
