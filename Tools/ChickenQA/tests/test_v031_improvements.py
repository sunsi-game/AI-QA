import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from chickenqa.cli import main
from chickenqa.parser import redact, analyze_file
from chickenqa.ai import build_ai_payload


class Improvements031Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'ChickenFight.uproject'
        self.project.write_text('{}', encoding='utf-8')
        self.folder = self.root / 'Saved' / 'Logs'
        self.folder.mkdir(parents=True)

    def add_log(self, name, data, ts):
        p = self.folder / name
        p.write_text(data, encoding='utf-8')
        os.utime(p,(ts,ts))
        return p

    def test_query_string_redacted(self):
        raw = 'LogHttp: Warning: url=[https://example.invalid/a?SessionID=SECRETSESSION&UserID=SECRETUSER] refs=[2]'
        sanitized = redact(raw)
        self.assertNotIn('SECRETSESSION', sanitized)
        self.assertNotIn('SECRETUSER', sanitized)
        self.assertIn('https://example.invalid/a?', sanitized)
        self.assertIn('QUERY_REDACTED', sanitized)

    def test_user_id_key_value_redacted(self):
        sanitized = redact('LogTemp: UserID=abc123 SessionID=xyz987')
        self.assertNotIn('abc123', sanitized)
        self.assertNotIn('xyz987', sanitized)

    def test_preview_redacts_http_query(self):
        log=self.add_log('ChickenFight.log', 'LogHttp: Warning: url=[https://example.invalid/collect?UserID=private]\n', 1600000000)
        preview=build_ai_payload(analyze_file(log))
        self.assertNotIn('private',json.dumps(preview))

    def test_log_listing_shows_recent_order_no_report(self):
        self.add_log('older.log', 'LogTemp: Warning: older',1600000000)
        self.add_log('newer.log', 'LogTemp: Warning: newer',1600000060)
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(['--project',str(self.project),'--list-logs'])
        self.assertEqual(code,0)
        text=output.getvalue()
        self.assertLess(text.find('newer.log'),text.find('older.log'))

    def test_old_log_warning_in_report(self):
        self.add_log('veryold.log', 'LogTemp: Warning: old',1600000000)
        out=self.root / 'out'
        with contextlib.redirect_stdout(io.StringIO()):
            code=main(['--project',str(self.project),'--out',str(out)])
        self.assertEqual(code,0)
        report=(out/'report.md').read_text(encoding='utf-8')
        self.assertIn('현재 게임 플레이 기록이 아닐 수',report)

    def test_listing_rejects_ai_option(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                main(['--project',str(self.project),'--list-logs','--ai'])
        self.assertEqual(ctx.exception.code, 2)

if __name__=='__main__':
    unittest.main()
