import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chickenqa.ai import build_ai_payload
from chickenqa.cli import main
from chickenqa.parser import analyze_file
from chickenqa.signals import find_signals


class AiWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.log = self.root / 'ChickenFight.log'
        self.log.write_text(
            'LoginId: SENSITIVE123\n'
            'EpicAccountId: SENSITIVE987\n'
            'LogChickenCollision: PushApply Target=Chicken_1\n'
            'LogChickenMovement: MovementUpdate Velocity=(X=nan,Y=12,Z=2)\n'
            'LogTemp: Warning: user C:\\Users\\PrivateOne\\Desktop\\Game\n'
            'Unhandled Exception: EXCEPTION_ACCESS_VIOLATION reading address 0xffffffffffffffff\n'
            'UnrealEditor_DKUEndGame!AChickenCharacter::~AChickenCharacter()\n',
            encoding='utf-8'
        )

    def test_event_field_not_counted_as_event(self):
        self.log.write_text('LogChickenMovement: MovementUpdate Dt=0.016 Fallen=0 Pending=0\n', encoding='utf-8')
        summary = analyze_file(self.log)
        self.assertEqual(summary['events'], {'MovementUpdate': 1})
        self.assertEqual(summary['gameplay_samples'][0]['event'], 'MovementUpdate')

    def test_finite_nonfinite_signals_are_distinguished(self):
        summary = analyze_file(self.log)
        signals = find_signals(summary)
        ids = [signal['code'] for signal in signals]
        self.assertIn('NONFINITE_GAMEPLAY_VALUE', ids)
        self.assertIn('CRASH_LOG_PRESENT', ids)
        self.assertIn('PUSH_FOLLOWUP_NOT_OBSERVED', ids)
        self.assertIn('TEST_RESULT_NOT_AVAILABLE', ids)
        nonfinite = next(x for x in signals if x['code'] == 'NONFINITE_GAMEPLAY_VALUE')
        self.assertEqual(nonfinite['evidence_lines'], [4])

    def test_prepare_ai_is_local_and_redacted(self):
        out = self.root / 'prepare'
        with patch('chickenqa.cli.analyze_with_gemini') as send:
            code = main(['--log', str(self.log), '--prepare-ai', '--out', str(out)])
            send.assert_not_called()
        self.assertEqual(code, 0)
        payload = json.loads((out / 'ai_payload_preview.json').read_text(encoding='utf-8'))
        joined = json.dumps(payload)
        for forbidden in ('SENSITIVE123', 'SENSITIVE987', 'PrivateOne', str(self.root)):
            self.assertNotIn(forbidden, joined)
        self.assertNotIn('ai_payload_preview.json', json.dumps(json.loads((out/'summary.json').read_text())))
        summary = json.loads((out/'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['ai_status'], 'preview_only')
        self.assertIn('API 호출은 하지 않았습니다', (out/'report.md').read_text(encoding='utf-8'))

    def test_ai_with_reviewed_payload_passes_exact_data(self):
        preview_dir = self.root / 'prepare'
        self.assertEqual(main(['--log', str(self.log), '--prepare-ai', '--out', str(preview_dir)]), 0)
        payload_path = preview_dir / 'ai_payload_preview.json'
        reviewed = json.loads(payload_path.read_text(encoding='utf-8'))
        reviewed['gameplay_samples'] = []  # user may remove information before submission
        payload_path.write_text(json.dumps(reviewed, ensure_ascii=False), encoding='utf-8')
        out = self.root / 'send'
        with patch('chickenqa.cli.analyze_with_gemini', return_value='## 관측 사실\nL6에서 충돌 관련 오류가 확인됨') as send:
            code = main(['--log', str(self.log), '--ai', '--ai-payload', str(payload_path), '--out', str(out)])
            self.assertEqual(send.call_args.kwargs['payload'], reviewed)
        self.assertEqual(code, 0)
        self.assertIn('## 관측 사실', (out / 'report.md').read_text(encoding='utf-8'))
        self.assertEqual(json.loads((out / 'summary.json').read_text(encoding='utf-8'))['ai_status'], 'completed')

    def test_ai_failure_keeps_local_report_and_nonzero_exit(self):
        out = self.root / 'fail'
        with patch('chickenqa.cli.analyze_with_gemini', side_effect=RuntimeError('quota exceeded')):
            code = main(['--log', str(self.log), '--ai', '--out', str(out)])
        self.assertEqual(code, 2)
        self.assertTrue((out / 'report.md').is_file())
        self.assertEqual(json.loads((out / 'summary.json').read_text(encoding='utf-8'))['ai_status'], 'failed')

    def test_changed_log_blocks_old_preview(self):
        preview_dir = self.root / 'prepare'
        main(['--log', str(self.log), '--prepare-ai', '--out', str(preview_dir)])
        self.log.write_text(self.log.read_text(encoding='utf-8') + 'LogTemp: Warning: changed\n', encoding='utf-8')
        with patch('chickenqa.cli.analyze_with_gemini') as send:
            code = main(['--log', str(self.log), '--ai', '--ai-payload', str(preview_dir/'ai_payload_preview.json'), '--out', str(self.root/'new')])
            send.assert_not_called()
        self.assertEqual(code, 2)

    def test_no_untrusted_claim_of_test_success(self):
        summary = analyze_file(self.log)
        payload = build_ai_payload(summary)
        self.assertEqual(payload['counts']['test_passed'], 0)
        self.assertNotIn('Project', json.dumps(payload))


if __name__ == '__main__':
    unittest.main()
