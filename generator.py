"""Deterministic raw sources; no analytics or model processing."""
from __future__ import annotations

import io
import json
import uuid
import wave
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
LIBRARY = ROOT / "data" / "library"
EVENTS = ROOT / "data" / "events"
FLAVORS = ("vanilla", "chocolate", "strawberry")
COLORS = {"vanilla": "#FFF8E7", "chocolate": "#795039", "strawberry": "#ED8AA8"}
BACKGROUND = "#E5E7EB"
TONES = {"Low": 220, "Middle": 440, "High": 880}
SAMPLE_RATE = 16000
DURATION = 10
AMPLITUDE = 0.20
STORY = (
    "I woke up wanting {flavor} ice cream. I knew the little shop near the park "
    "sold {flavor}, so I put on my shoes and walked down the familiar street. "
    "Along the way, I imagined the taste of {flavor} and watched the morning "
    "traffic pass. At the shop, I asked for {flavor} ice cream in a cone. "
    "I carried my {flavor} treat to a bench outside and enjoyed it slowly "
    "before walking home."
)


def image_bytes(flavor: str, scoops: int) -> bytes:
    if flavor not in FLAVORS or scoops not in (1, 2, 3):
        raise ValueError("Choose a known flavor and one to three scoops.")
    image = Image.new("RGB", (512, 640), BACKGROUND)
    draw = ImageDraw.Draw(image)
    # The entire scene stays fixed. Extra scoops stack upward into reserved space.
    draw.polygon([(196, 349), (316, 349), (256, 592)], fill="#C78A45")
    draw.line([(196, 349), (256, 592), (316, 349)], fill="#9C652F", width=3)
    for index in range(scoops):
        center_y = 320 - 96 * index
        draw.ellipse((189, center_y - 67, 323, center_y + 67), fill=COLORS[flavor])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def audio_bytes(tone: str) -> bytes:
    frequency = TONES[tone]
    count = SAMPLE_RATE * DURATION
    time = np.arange(count, dtype=np.float64) / SAMPLE_RATE
    signal = AMPLITUDE * np.sin(2 * np.pi * frequency * time)
    # The same 10 ms onset/offset envelope avoids playback clicks for every tone.
    fade = int(0.01 * SAMPLE_RATE)
    envelope = np.linspace(0, 1, fade)
    signal[:fade] *= envelope
    signal[-fade:] *= envelope[::-1]
    pcm = np.rint(signal * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())
    return buffer.getvalue()


def story_text(flavor: str) -> str:
    if flavor not in FLAVORS:
        raise ValueError("Unknown flavor")
    return STORY.format(flavor=flavor)


def build_library(root: Path = LIBRARY) -> None:
    for folder in ("image", "audio", "text"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    for flavor in FLAVORS:
        for scoops in (1, 2, 3):
            (root / "image" / f"{flavor}_{scoops}.png").write_bytes(image_bytes(flavor, scoops))
        (root / "text" / f"{flavor}.txt").write_text(story_text(flavor), encoding="utf-8")
    for tone in TONES:
        (root / "audio" / f"{tone.lower()}.wav").write_bytes(audio_bytes(tone))


def save_event(image_flavor: str, scoops: int, tone: str, text_flavor: str,
               root: Path = EVENTS, library: Path = LIBRARY) -> tuple[Path, bytes]:
    """Snapshot the current choices. Metadata records truth, never derived features."""
    if image_flavor not in FLAVORS or text_flavor not in FLAVORS or tone not in TONES or scoops not in (1, 2, 3):
        raise ValueError("Invalid source selection")
    now = datetime.now(timezone.utc)
    event_id = f"event_{now.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    directory = root / event_id
    directory.mkdir(parents=True, exist_ok=False)
    sources = {
        "image.png": library / "image" / f"{image_flavor}_{scoops}.png",
        "audio.wav": library / "audio" / f"{tone.lower()}.wav",
        "text.txt": library / "text" / f"{text_flavor}.txt",
    }
    for filename, source in sources.items():
        (directory / filename).write_bytes(source.read_bytes())
    manifest = {
        "schema_version": 1,
        "event_id": event_id,
        "event_time": now.isoformat(),
        "time_basis": "UTC snapshot creation; no simulated clock in this version",
        "sources": {
            "image": {"file": "image.png", "flavor": image_flavor, "scoops": scoops},
            "audio": {"file": "audio.wav", "tone": tone, "frequency_hz": TONES[tone],
                      "duration_seconds": DURATION, "sample_rate_hz": SAMPLE_RATE,
                      "amplitude_peak_fraction": AMPLITUDE, "fade_seconds": 0.01},
            "text": {"file": "text.txt", "flavor": text_flavor,
                     "word_count": len(story_text(text_flavor).split())},
        },
        "note": "Generator settings are ground-truth metadata, not analytical input features.",
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename in (*sources, "manifest.json"):
            archive.write(directory / filename, arcname=f"{event_id}/{filename}")
    return directory, buffer.getvalue()


if __name__ == "__main__":
    build_library()
    print(f"Stored 9 PNG images, 3 WAV tones, and 3 text stories in {LIBRARY}")
