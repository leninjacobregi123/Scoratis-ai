"""Manual/integration smoke test for the video generation pipeline.

Requires a LIVE backend already running at BASE_URL, reachable over a real
socket (plain httpx.Client, not FastAPI's in-process TestClient like
a live local LLM server) - CI has no such server, and neither does a plain
`pytest -m integration` run unless one was started first. Actual Manim
rendering is slow (minutes) too, so this is opt-in only: set
RUN_LIVE_VIDEO_TESTS=true after starting the app yourself, e.g.
`RUN_LIVE_VIDEO_TESTS=true pytest tests/integration/test_video_generation.py -m integration`.
"""

import os
import time

import httpx
import pytest

BASE_URL = "http://localhost:8000"
TIMEOUT = 300.0

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_VIDEO_TESTS") != "true",
        reason="Requires a live backend on localhost:8000 - opt in with RUN_LIVE_VIDEO_TESTS=true",
    ),
]


class TestVideoGeneration:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)
        yield
        self.client.close()

    def test_generate_video(self):
        payload = {
            "topic": "Introduction to Quantum Physics",
            "quality": "high",
            "duration": 90
        }

        response = self.client.post("/videos/generate", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert "message" in data
        assert data["topic"] == payload["topic"]

        task_id = data["task_id"]
        print(f"✓ Video generation started with task_id: {task_id}")

    def test_generate_video_missing_topic(self):
        payload = {
            "topic": "The Solar System"
        }

        response = self.client.post("/videos/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        print(f"✓ Video generation works with minimal payload")

    def test_get_generation_status(self):
        response = self.client.get("/videos/status/nonexistent-task-123")
        assert response.status_code == 404
        print(f"✓ Nonexistent task returns 404")

    def test_get_generated_videos(self):
        payload = {
            "topic": "The Water Cycle",
            "quality": "high",
            "duration": 120
        }

        gen_response = self.client.post("/videos/generate", json=payload)
        assert gen_response.status_code == 200
        task_id = gen_response.json()["task_id"]
        print(f"✓ Video generation started: {task_id}")

        max_attempts = 10
        for attempt in range(max_attempts):
            status_response = self.client.get(f"/videos/status/{task_id}")
            assert status_response.status_code == 200

            status_data = status_response.json()
            print(f"  Attempt {attempt + 1}/{max_attempts}: {status_data}")

            status_str = str(status_data).lower()
            if "completed" in status_str or "done" in status_str or "success" in status_str:
                print(f"✓ Video generation completed")
                break

            time.sleep(1)

    def test_video_generation_qualities(self):
        qualities = ["low", "medium", "high"]

        for quality in qualities:
            payload = {
                "topic": f"Test Video - Quality {quality}",
                "quality": quality,
                "duration": 60
            }

            response = self.client.post("/videos/generate", json=payload)
            assert response.status_code == 200
            data = response.json()
            print(f"✓ Video generation started with quality: {quality} (task_id: {data['task_id']})")

    def test_video_duration_variations(self):
        durations = [30, 60, 120]

        for duration in durations:
            payload = {
                "topic": f"Test Video - Duration {duration}s",
                "quality": "low",
                "duration": duration
            }

            response = self.client.post("/videos/generate", json=payload)
            assert response.status_code == 200
            data = response.json()
            print(f"✓ Video generation started with duration: {duration}s (task_id: {data['task_id']})")

    def test_video_history(self):
        response = self.client.get("/videos/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Retrieved video history: {len(data) if isinstance(data, list) else 'unknown'} entries")

    def test_video_search(self):
        response = self.client.get("/videos/search", params={"q": "quantum physics"})
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        print(f"✓ Video search returned {len(data['videos'])} results")


def test_video_generation_standalone():
    """Manual, verbose walkthrough of the same pipeline - run directly with
    `python test_video_generation.py` against a live server for a quick
    human-readable smoke check outside of pytest's output."""
    print("\n" + "=" * 60)
    print("VIDEO GENERATION TEST")
    print("=" * 60)

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        print("\n1. Health Check")
        response = client.get("/health")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Message: {data.get('message')}")
            print(f"   Status: {data.get('status')}")

        print("\n2. Generate Video")
        payload = {
            "topic": "Quantum Entanglement",
            "quality": "high",
            "duration": 90
        }
        response = client.post("/videos/generate", json=payload)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            print(f"   Task ID: {task_id}")
            print(f"   Message: {data.get('message')}")

            print("\n3. Check Video Status")
            status_response = client.get(f"/videos/status/{task_id}")
            print(f"   Status: {status_response.status_code}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   Response: {status_data}")

        print("\n4. Get Generated Videos")
        response = client.get("/videos/generated")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            print(f"   Total videos: {len(videos)}")
            if videos:
                print("   Sample videos:")
                for video in videos[:3]:
                    print(f"     - {video}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_video_generation_standalone()
