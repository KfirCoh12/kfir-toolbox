import subprocess
import unittest
from unittest.mock import MagicMock, patch

from desktop_launcher import find_free_port, stop_server, wait_for_streamlit


class DesktopLauncherTests(unittest.TestCase):
    def test_free_port_is_loopback_tcp_port(self):
        port = find_free_port()
        self.assertGreater(port, 0)
        self.assertLessEqual(port, 65535)

    @patch("desktop_launcher.urllib.request.urlopen")
    def test_wait_for_streamlit_returns_when_health_is_200(self, urlopen):
        response = MagicMock()
        response.status = 200
        urlopen.return_value.__enter__.return_value = response
        process = MagicMock()
        process.poll.return_value = None

        wait_for_streamlit("http://127.0.0.1:8765", process, timeout=0.1)

        urlopen.assert_called_once_with(
            "http://127.0.0.1:8765/_stcore/health", timeout=1.5
        )

    def test_wait_for_streamlit_reports_early_process_exit(self):
        process = MagicMock()
        process.poll.return_value = 1
        process.returncode = 1

        with self.assertRaisesRegex(RuntimeError, "exited during startup"):
            wait_for_streamlit("http://127.0.0.1:8765", process, timeout=0.1)

    def test_stop_server_terminates_running_process(self):
        process = MagicMock()
        process.poll.return_value = None

        stop_server(process)

        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=5)

    def test_stop_server_uses_kill_after_terminate_timeout(self):
        process = MagicMock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("python", 5), None]

        stop_server(process)

        process.kill.assert_called_once_with()
        self.assertEqual(process.wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
