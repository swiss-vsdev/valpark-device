"""Checks minimaux : machine d'états, file persistante, parseur GNSS, rendu."""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valpark.config import Config
from valpark.detector import Detector
from valpark.display import Display
from valpark.main import read_token
from valpark.queue import EventQueue
from valpark.sensors import Sample, parse_cgpsinfo


class DetectorTest(unittest.TestCase):
    def test_parked_then_departed(self):
        detector = Detector(Config())
        calm = Sample(None, "none", 46.2, 7.3, 0.0, 0.0)
        moving = Sample(None, "none", 46.2, 7.3, 30.0, 500.0)
        self.assertEqual(detector.update(calm), [])
        self.assertEqual(detector.update(calm), ["PARKED"])
        self.assertEqual(detector.update(calm), [])
        self.assertEqual(detector.update(moving), ["DEPARTED"])

    def test_heartbeat_while_moving(self):
        cfg = Config(heartbeat_s=0)
        detector = Detector(cfg)
        moving = Sample(None, "none", 46.2, 7.3, 30.0, 500.0)
        self.assertEqual(detector.update(moving), ["HEARTBEAT"])


class QueueTest(unittest.TestCase):
    def test_seq_survives_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = EventQueue(Path(tmp) / "events.sqlite3")
            first = queue.add("BOOT")
            second = queue.add("PARKED", lat=46.2, lon=7.3)
            self.assertEqual([e["seq"] for e in queue.pending()], [1, 2])
            self.assertEqual(second["lat"], 46.2)
            queue.remove([first["seq"], second["seq"]])
            self.assertEqual(queue.size(), 0)
            third = queue.add("DEPARTED")
            self.assertEqual(third["seq"], 3)


class TokenTest(unittest.TestCase):
    def test_missing_or_placeholder_exits_78(self):
        cfg = Config(server_base="http://host:4321", token_path="/nonexistent/token")
        with self.assertRaises(SystemExit) as missing:
            read_token(cfg)
        self.assertEqual(missing.exception.code, os.EX_CONFIG)

        with tempfile.TemporaryDirectory() as tmp:
            token = Path(tmp) / "device.token"
            token.write_text("secret")
            cfg = Config(server_base="http://<SERVER_LAN_IP>:4321", token_path=token)
            with self.assertRaises(SystemExit) as placeholder:
                read_token(cfg)
            self.assertEqual(placeholder.exception.code, os.EX_CONFIG)

            cfg = Config(server_base="http://host:4321", token_path=token)
            self.assertEqual(read_token(cfg), "secret")


class GnssTest(unittest.TestCase):
    def test_parse_cgpsinfo(self):
        line = "4622.79569,N,00721.46332,E,171126,080211,456.7,0.0,0.0"
        sample = parse_cgpsinfo(line)
        self.assertIsNotNone(sample)
        self.assertAlmostEqual(sample.lat, 46.379928, places=4)
        self.assertAlmostEqual(sample.lon, 7.357722, places=4)
        self.assertEqual(sample.time_source, "gnss")
        self.assertIsNone(parse_cgpsinfo(",,,,"))


class DisplayTest(unittest.TestCase):
    def test_mock_truncates_to_22_chars(self):
        display = Display(Config(mock=True))
        output = io.StringIO()
        with redirect_stdout(output):
            display.render({
                "version": "abc",
                "icon": "paid",
                "line1": "X" * 40,
                "line2": "Actif depuis 13:12",
                "line3": "",
                "inverted": True,
            })
        self.assertIn("X" * 22, output.getvalue())
        self.assertNotIn("X" * 23, output.getvalue())


if __name__ == "__main__":
    unittest.main()
