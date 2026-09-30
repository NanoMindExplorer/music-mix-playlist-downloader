"""
Tests for mmpd.web and Web Browser Interface.
"""

from __future__ import annotations

import json
import pytest
from mmpd.web import create_app, TaskManager, JobTask


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"MUSIC MIX & PLAYLIST DOWNLOADER" in res.data
    assert b"Downloader" in res.data
    assert b"Library & Player" in res.data
    assert b"Retrofit Engine" in res.data


def test_api_config(client):
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.get_json()
    assert "version" in data
    assert "output_dir" in data


def test_api_doctor(client):
    res = client.get("/api/doctor")
    assert res.status_code == 200
    data = res.get_json()
    assert "python_version" in data
    assert "ffmpeg_ok" in data


def test_api_library_empty(client):
    res = client.get("/api/library")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_api_download_validation(client):
    # Empty URL should return 400
    res = client.post("/api/download", json={"url": ""})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_api_task_not_found(client):
    res = client.get("/api/task/not-exist")
    assert res.status_code == 404


def test_task_manager_model():
    tm = TaskManager()
    task = JobTask(
        task_id="test1234",
        task_type="download",
        status="queued",
        url="https://youtube.com/watch?v=example",
        options={},
    )
    task.add_log("Hello log", level="info")
    d = task.to_dict()
    assert d["task_id"] == "test1234"
    assert len(d["logs"]) == 1
    assert d["logs"][0]["msg"] == "Hello log"
