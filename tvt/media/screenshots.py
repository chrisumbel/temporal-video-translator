"""Extract screenshots from staged videos with ffmpeg into the scratch container."""

import logging
import os
import subprocess
import tempfile

from dotenv import load_dotenv

from tvt.azure import blob_store
from tvt.media import downloader

load_dotenv()

SCRATCH_SCREENSHOT_CONTAINER = os.environ["SCRATCH_SCREENSHOT_CONTAINER"]

# keep uploads and gpt-4o vision input small
SCREENSHOT_WIDTH = 960

SCREENSHOT_FRACTIONS = (0.25, 0.5, 0.75)

logger = logging.getLogger(__name__)


def _duration_seconds(path):
    """Video duration via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _grab_frame(video_path, at_seconds, out_path):
    """Write one scaled screenshot taken at at_seconds."""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(at_seconds), "-i", video_path,
         "-frames:v", "1", "-vf", f"scale={SCREENSHOT_WIDTH}:-1", "-y", out_path],
        capture_output=True, check=True,
    )


def _screenshot_times(duration):
    """Screenshots at the 25%, 50%, and 75% points of the video."""
    return [duration * fraction for fraction in SCREENSHOT_FRACTIONS if duration > 0]


def extract_screenshots(video_blob_name):
    """Grab screenshots from a staged video; return their scratch-container
    blob names."""
    stem = os.path.splitext(video_blob_name)[0]
    blob_names = []

    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "video")
        with open(video_path, "wb") as out:
            downloader.open_video(video_blob_name).readinto(out)

        duration = _duration_seconds(video_path)
        times = _screenshot_times(duration)
        logger.info("Extracting %d screenshots from %s (%.1fs)",
                    len(times), video_blob_name, duration)

        for i, at in enumerate(times, start=1):
            frame_path = os.path.join(tmp, f"frame-{i}.jpg")
            _grab_frame(video_path, at, frame_path)

            blob_name = f"{stem}-{i}.jpg"
            with open(frame_path, "rb") as frame:
                blob_store.upload_blob(SCRATCH_SCREENSHOT_CONTAINER, blob_name,
                                       frame, content_type="image/jpeg")
            blob_names.append(blob_name)

    logger.info("Extracted %s", blob_names)
    return blob_names
