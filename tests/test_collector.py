import subprocess
import os
import stat
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

    @unittest.skipUnless(os.name == "posix", "POSIX directory mode")
    def test_new_capture_evidence_folder_is_private(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "capture"
            collector.capture(HOME, "wap1", folder,
                              resolver=lambda *args, **kwargs: [],
                              runner=mock.Mock())
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)

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


    def test_anonymous_cookie_requires_exact_single_host_only_token(self):
        value = b"0123456789abcdef0123456789ABCDEF"
        accepted = (b"HTTP/1.1 200 OK\r\n"
                    b"Set-Cookie: JSESSIONID=" + value
                    + b"; Path=/; HttpOnly\r\n\r\n")
        self.assertEqual(collector.anonymous_jsessionid(accepted),
                         value.decode("ascii"))
        bad = [
            b"HTTP/1.1 200 OK\r\n\r\n",
            accepted.replace(b"Path=/", b"Domain=.tx.com.cn; Path=/"),
            accepted.replace(value, b"a\r\nInjected: true"),
            accepted.replace(value, b"bad"),
            accepted.replace(b"\r\n\r\n", b"\r\nSet-Cookie: JSESSIONID=" +
                             value + b"; Path=/\r\n\r\n"),
        ]
        for raw in bad:
            with self.subTest(raw=raw[:45]), self.assertRaises(ValueError):
                collector.anonymous_jsessionid(raw)

    def test_anonymous_cookie_replay_https_and_no_persisted_secret(self):
        session = "0123456789abcdef0123456789ABCDEF"
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "sample"
            def runner(command, **kwargs):
                self.assertEqual(command[command.index("--request")+1], "GET")
                self.assertNotIn("--location", command)
                self.assertIn("--cookie", command)
                cookie_path = Path(command[command.index("--cookie")+1])
                self.assertEqual(cookie_path.stat().st_mode & 0o777, 0o600)
                data = cookie_path.read_text(encoding="ascii")
                self.assertIn("tx.com.cn\tFALSE\t/\tTRUE\t0\tJSESSIONID\t" + session, data)
                self.assertNotIn(session, " ".join(
                    part for part in command if part != str(cookie_path)
                ))
                headers = b"HTTP/1.1 302 Found\r\nLocation: http://tx.com.cn/in/guest.do\r\nContent-Length: 0\r\n\r\n"
                Path(command[command.index("--dump-header")+1]).write_bytes(headers)
                Path(command[command.index("--output")+1]).write_bytes(b"")
                return subprocess.CompletedProcess(command, 0, stdout=(
                    b"302\nhttps://tx.com.cn/zone/cs/category.do\n8.8.8.8\n\n"
                ), stderr=b"")
            result = collector.capture(
                "https://tx.com.cn/zone/cs/category.do", "wap1",
                folder, resolver=DNS, runner=runner, session_cookie=session)
            self.assertEqual(result["classification"], "REDIRECT")
            self.assertEqual(result["anonymous_cookie_sent"], ["JSESSIONID"])
            self.assertEqual(list(folder.glob(".anon_session_*")), [])
            self.assertNotIn(session,
                (folder / "metadata.json").read_text(encoding="utf-8"))
            self.assertNotIn(session,
                (folder / "curl_writeout.txt").read_text(encoding="utf-8"))
            self.assertEqual(result["A_navigation"], "PENDING")

    def test_anonymous_cookie_rejected_on_http_and_other_host(self):
        session = "0123456789abcdef0123456789ABCDEF"
        with tempfile.TemporaryDirectory() as root:
            for idx, url in enumerate((
                "http://tx.com.cn/zone/cs/category.do",
                "https://example.org/category.do",
            )):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    collector.capture(url, "wap1", Path(root) / str(idx),
                                      resolver=DNS, session_cookie=session)
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_no_network_without_execute(self):
        with mock.patch("wap_probe.collector.capture") as capture:
            result=collector.main(["--url",HOME])
            capture.assert_not_called()
        self.assertEqual(result,0)

if __name__=="__main__":
    unittest.main()
