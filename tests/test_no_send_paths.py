import unittest
from pathlib import Path


class NoSendPathsTests(unittest.TestCase):
    def test_phase_one_source_contains_no_email_send_endpoint(self):
        source_root = Path(__file__).resolve().parents[1] / "src"
        source = "\n".join(
            path.read_text()
            for path in source_root.rglob("*.py")
        )
        for forbidden in (
            "/messages/send",
            "/drafts/send",
            "/approve-email",
            "Approve + Send",
            "Force Send",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
