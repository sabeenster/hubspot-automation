import base64
import hashlib
import hmac
import time
import unittest
from unittest.mock import patch

from src.agentway_leads.webhooks import verify_hubspot_signature


class HubSpotWebhookSignatureTests(unittest.TestCase):
    def test_validates_legacy_v1_signature(self):
        secret = "client-secret"
        body = b'[{"objectId":123}]'
        signature = hashlib.sha256(secret.encode() + body).hexdigest()
        self.assertTrue(
            verify_hubspot_signature(
                body,
                secret,
                signature=signature,
            )
        )
        self.assertFalse(
            verify_hubspot_signature(
                body + b"tampered",
                secret,
                signature=signature,
            )
        )

    def test_validates_v3_signature_and_rejects_old_timestamp(self):
        secret = "client-secret"
        method = "POST"
        uri = "https://automation.example.com/webhooks/hubspot"
        body = b'[{"objectId":123}]'
        now_ms = 1_800_000_000_000
        timestamp = str(now_ms)
        source = method.encode() + uri.encode() + body + timestamp.encode()
        signature = base64.b64encode(
            hmac.new(secret.encode(), source, hashlib.sha256).digest()
        ).decode()

        with patch("src.agentway_leads.webhooks.time.time", return_value=now_ms / 1000):
            self.assertTrue(
                verify_hubspot_signature(
                    body,
                    secret,
                    signature_v3=signature,
                    timestamp=timestamp,
                    method=method,
                    uri=uri,
                )
            )

        old_timestamp = str(now_ms - 6 * 60 * 1000)
        with patch("src.agentway_leads.webhooks.time.time", return_value=now_ms / 1000):
            self.assertFalse(
                verify_hubspot_signature(
                    body,
                    secret,
                    signature_v3=signature,
                    timestamp=old_timestamp,
                    method=method,
                    uri=uri,
                )
            )


if __name__ == "__main__":
    unittest.main()
