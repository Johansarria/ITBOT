import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

# This is a bit of a hack to make the import work when running directly
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.alerta_manager import Alerter, SeverityLevel

class TestAlerter(unittest.TestCase):

    def setUp(self):
        """Reset the singleton instance before each test."""
        Alerter._instance = None
        self.alerter = Alerter()
        self.alerter.configure(bot_instance=AsyncMock(), chat_id=12345)

    @patch('utils.alerta_manager.send_telegram_message', new_callable=AsyncMock)
    def test_alert_formatting(self, mock_send_message):
        """Tests if the alert message is formatted correctly."""
        async def run():
            await self.alerter.send_alert(
                alert_key="test_formatting",
                severity=SeverityLevel.CRITICAL,
                source="FormatterTest",
                message="This is a test.",
                details={"code": 123}
            )

        asyncio.run(run())

        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args
        sent_text = call_args.args[2] # (bot, chat_id, text, ...)

        self.assertIn("🚨 *CRITICAL: FormatterTest*", sent_text)
        self.assertIn("This is a test.", sent_text)
        self.assertIn('"code": 123', sent_text)

    @patch('utils.alerta_manager.send_telegram_message', new_callable=AsyncMock)
    def test_deduplication_logic(self, mock_send_message):
        """Tests the alert suppression and re-sending logic."""

        async def run():
            # 1. Send the first alert, it should go through.
            await self.alerter.send_alert("dedup_test", SeverityLevel.WARNING, "Deduplication", "First message.")
            self.assertEqual(mock_send_message.call_count, 1)

            # 2. Send immediately again, it should be suppressed.
            await self.alerter.send_alert("dedup_test", SeverityLevel.WARNING, "Deduplication", "Second message, should be suppressed.")
            self.assertEqual(mock_send_message.call_count, 1) # No new call

            # 3. Change silence period and wait, it should go through.
            self.alerter._silence_period = timedelta(seconds=0.1)
            await asyncio.sleep(0.2)
            await self.alerter.send_alert("dedup_test", SeverityLevel.WARNING, "Deduplication", "Third message, should be sent.")
            self.assertEqual(mock_send_message.call_count, 2) # Should be called again

        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
