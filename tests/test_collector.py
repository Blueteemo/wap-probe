import subprocess
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from wap_probe import collector

HOME="http://tx.com.cn/"
DNS=lambda *a, **k: [(2,1,6,"",("8.8.8.8",0))]

class CollectorTests(unittest.TestCase):
    def test_matrix_32(self):
        tasks=collector.matrix()
        self.assertEqual(len(tasks), 32)
        self.assertEqual(len(set(tasks)),32)
        self.assertEqual(sum(1 for u,p in tasks if u.startswith("https:")),16)

    def test_url_guardrails(self):
        bad=["file:///etc/passwd", "http://127.0.0.1/",
             "http://example.com:8080/", "http://u:p@example.com/",
             "http://example.com/#foo", "http://x/", "http://a..b/",
             "http://example.com/%0d%0a", "http://example.com/../x",
             "http://example.com/x?sid=123", "http://example.com/x$(a)"]
        for url in bad:
            with self.subTest(url=url), self.assertRaises(ValueError):
                collector.validate_url(url)

    def test_dns_rejects_private_in_mix(self):
        def mixed(*a,**k):
            return [(2,1,6,"",("8.8.8.8",0)),(2,1,6,"",("10.0.0.4",0))]
        with self.assertRaises(ValueError):
            collector.public_dns("example.org",resolver=mixed)

    def test_dns_accepts_public(self):
        self.assertEqual(collector.public_dns("example.org",resolver=DNS),["8.8.8.8"])

    def test_command_disables_proxy_redirect_and_config(self):
        with tempfile.TemporaryDirectory() as d:
            cmd=collector.build_command(HOME,"tx.com.cn",80,"8.8.8.8","wap1",Path(d))
        self.assertEqual(cmd[:2],["curl","-q"])
        self.assertEqual(cmd[cmd.index("--request")+1],"GET")
        self.assertEqual(cmd[cmd.index("--noproxy")+1],"*")
        self.assertEqual(cmd[cmd.index("--proxy")+1],"")
        self.assertIn("tx.com.cn:80:8.8.8.8",cmd)
        self.assertNotIn("-L",cmd)
        self.assertNotIn("--location",cmd)
        self.assertNotIn("--insecure",cmd)

    def test_capture_failed_dns_never_calls_runner(self):
        def dns_error(*a,**k):
            raise socket.gaierror("lookup error")
        with tempfile.TemporaryDirectory() as d:
            runner=mock.Mock()
            m=collector.capture(HOME,"wap1",Path(d)/"one",resolver=dns_error,runner=runner)
            runner.assert_not_called()
            self.assertEqual(m["classification"],"DNS_OR_SAFETY_OR_TOOL_ERROR")
            self.assertEqual(m["A_origin"],"PENDING")
            self.assertEqual(len(m["body_sha256"]),64)

    def test_capture_creates_auditable_evidence(self):
        body=b"<wml><card id='x'/></wml>"
        headers=(b"HTTP/1.1 200 OK\r\nContent-Type: text/vnd.wap.wml\r\n"
                 +f"Content-Length: {len(body)}\r\n\r\n".encode())
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"one"
            def runner(cmd,**kwargs):
                Path(cmd[cmd.index("--output")+1]).write_bytes(body)
                Path(cmd[cmd.index("--dump-header")+1]).write_bytes(headers)
                return subprocess.CompletedProcess(cmd,0,stdout=(
                    f"200\n{HOME}\n8.8.8.8\ntext/vnd.wap.wml\n").encode(),stderr=b"")
            m=collector.capture(HOME,"wap1",p,resolver=DNS,runner=runner)
            self.assertEqual(m["classification"],"WML_CAPTURED_NEEDS_R5")
            self.assertEqual((p/"body.bin").read_bytes(),body)
            self.assertEqual(m["body_sha256"],collector.sha256(body))
            self.assertEqual(m["headers_sha256"],collector.sha256(headers))
            self.assertEqual(m["pinned_ip"],m["remote_ip"])
            self.assertEqual(m["A_navigation"],"PENDING")

    def test_no_network_without_execute(self):
        with mock.patch("wap_probe.collector.capture") as capture:
            result=collector.main(["--url",HOME])
            capture.assert_not_called()
        self.assertEqual(result,0)

if __name__=="__main__":
    unittest.main()
