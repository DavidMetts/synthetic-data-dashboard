import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageColor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generator as g


class SourcesTest(unittest.TestCase):
    def test_images_have_increasing_flavor_area_and_fixed_scene(self):
        for flavor in g.FLAVORS:
            arrays = [np.array(Image.open(io.BytesIO(g.image_bytes(flavor, n)))) for n in (1, 2, 3)]
            color = ImageColor.getrgb(g.COLORS[flavor])
            counts = [int(np.all(a == color, axis=2).sum()) for a in arrays]
            self.assertTrue(counts[0] < counts[1] < counts[2], (flavor, counts))
            self.assertEqual(arrays[0].shape, (640, 512, 3))
            for a in arrays[1:]:
                np.testing.assert_array_equal(a[388:], arrays[0][388:])
                np.testing.assert_array_equal(a[:, :180], arrays[0][:, :180])

    def test_audio_duration_frequency_and_amplitude(self):
        peaks = []
        for tone, expected_frequency in g.TONES.items():
            with wave.open(io.BytesIO(g.audio_bytes(tone)), "rb") as wav:
                self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()), (1, 2, 16000, 160000))
                samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(float)
            peaks.append(np.max(np.abs(samples)))
            middle = samples[16000:32000]
            spectrum = np.abs(np.fft.rfft(middle))
            self.assertEqual(np.argmax(spectrum), expected_frequency)
            self.assertGreater(spectrum[expected_frequency] ** 2 / np.sum(spectrum ** 2), 0.999)
            self.assertEqual(samples[0], 0)
            self.assertEqual(samples[-1], 0)
        self.assertLessEqual(max(peaks) - min(peaks), 1)

    def test_text_is_only_flavor_substitution(self):
        normalized = []
        for flavor in g.FLAVORS:
            text = g.story_text(flavor)
            self.assertLessEqual(len(text.split()), 100)
            self.assertEqual(text.count(flavor), 5)
            normalized.append(text.replace(flavor, "FLAVOR"))
        self.assertEqual(len(set(normalized)), 1)

    def test_event_preserves_separate_sources_and_choices(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            g.build_library(root / "library")
            event, archive = g.save_event("strawberry", 3, "Low", "chocolate", root / "events", root / "library")
            manifest = json.loads((event / "manifest.json").read_text())
            self.assertEqual(manifest["sources"]["image"]["flavor"], "strawberry")
            self.assertEqual(manifest["sources"]["text"]["flavor"], "chocolate")
            self.assertEqual(manifest["sources"]["audio"]["frequency_hz"], 220)
            with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                self.assertEqual(len(zipped.namelist()), 4)
                for name in ("image.png", "audio.wav", "text.txt", "manifest.json"):
                    self.assertEqual(zipped.read(f"{event.name}/{name}"), (event / name).read_bytes())

    def test_dashboard_controls(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(g.ROOT / "app.py")).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([tab.label for tab in app.tabs], ["Image", "Audio", "Text"])
        app.selectbox[0].select("strawberry")
        app.radio[0].set_value(3)
        app.selectbox[1].select("High")
        app.selectbox[2].select("chocolate")
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.selectbox[0].value, "strawberry")
        self.assertEqual(app.selectbox[2].value, "chocolate")
        self.assertTrue(any("strawberry, 3 scoop(s)" in item.value for item in app.markdown))

    def test_dashboard_saves_to_separate_session_folders(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as directory, patch.object(g, "EVENTS", Path(directory)):
            sessions = []
            for _ in range(2):
                app = AppTest.from_file(str(g.ROOT / "app.py")).run(timeout=20)
                app.button[0].click().run()
                self.assertEqual(len(app.exception), 0)
                saved = app.session_state["last_event"]
                event = Path(saved["directory"])
                self.assertTrue((event / "manifest.json").exists())
                self.assertEqual(len(zipfile.ZipFile(io.BytesIO(saved["archive"])).namelist()), 4)
                sessions.append(event.parent)
            self.assertNotEqual(sessions[0], sessions[1])

    def test_missing_assets_show_clear_error(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as directory, patch.object(g, "LIBRARY", Path(directory)):
            app = AppTest.from_file(str(g.ROOT / "app.py")).run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertIn("source files are missing", app.error[0].value)


if __name__ == "__main__":
    unittest.main()
