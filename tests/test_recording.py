import json
import os
import tempfile

import pytest

from human_player.recording import RecordingManager


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def rm(tmp_dir, monkeypatch):
    monkeypatch.setattr("human_player.recording.RECORDINGS_DIR", tmp_dir)
    return RecordingManager()


class TestRecordingManager:
    def test_start_session(self, rm):
        sid = rm.start_session("ABCD")
        assert sid.startswith("ABCD_")
        assert rm.current_session_id == sid
        rm.end_session()

    def test_record_step(self, rm):
        from arcengine import GameAction
        rm.start_session("ABCD")
        rm.record_step(GameAction.ACTION1, None, None, 1, 100)
        rm.end_session()
        assert rm.current_session_id is None

    def test_end_session_closes_file(self, rm):
        rm.start_session("ABCD")
        rm.end_session()
        assert rm.current_file is None
        assert rm.current_session_id is None

    def test_list_recordings(self, rm, tmp_dir):
        rm.start_session("ABCD")
        rm.end_session()
        recordings = rm.list_recordings("ABCD")
        assert len(recordings) >= 1

    def test_load_recording(self, rm, tmp_dir):
        from arcengine import GameAction
        rm.start_session("ABCD")
        rm.record_step(GameAction.ACTION1, None, None, 1, 100)
        rm.end_session()
        recordings = rm.list_recordings("ABCD")
        if recordings:
            records = rm.load_recording(recordings[0]["filepath"])
            assert len(records) >= 1
            assert records[0]["action"] == "ACTION1"
