import json
import os
import tempfile
import unittest
from pathlib import Path
from chickenqa.cli import main
from chickenqa.discovery import find_project_logs, select_latest_log
from chickenqa.parser import analyze_file


class RealGameLogsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'ChickenFight.uproject'
        self.project.write_text('{}', encoding='utf-8')
        self.log_dir = self.root / 'Saved' / 'Logs'
        self.log_dir.mkdir(parents=True)

    def make_log(self, name, contents, timestamp):
        path = self.log_dir / name
        path.write_text(contents, encoding='utf-8')
        os.utime(path, (timestamp, timestamp))
        return path

    def test_select_newest_by_modified_time(self):
        self.make_log('ChickenFight.log', 'LogTemp: Warning: old', 1600000000)
        latest = self.make_log('ChickenFight-backup.log', 'LogTemp: Error: newer', 1600000008)
        self.assertEqual(find_project_logs(self.project)[0], latest)
        selected, meta = select_latest_log(self.project)
        self.assertEqual(selected, latest)
        self.assertEqual(meta['candidate_log_count'], 2)
        self.assertEqual(meta['relative_log_path'], 'Saved/Logs/ChickenFight-backup.log')

    def test_crash_folder_included(self):
        self.make_log('ChickenFight.log', 'LogTemp: Warning: older', 1600000000)
        crash_folder = self.root / 'Saved' / 'Crashes' / 'UECC-test'
        crash_folder.mkdir(parents=True)
        crash_file = crash_folder / 'Crash.log'
        crash_file.write_text('Fatal error: crash', encoding='utf-8')
        os.utime(crash_file, (1600000009, 1600000009))
        selected, meta = select_latest_log(self.project)
        self.assertEqual(selected, crash_file)
        self.assertEqual(meta['candidate_log_count'], 2)

    def test_missing_logs_error(self):
        with self.assertRaisesRegex(FileNotFoundError, '프로젝트 로그를 찾지 못했습니다'):
            select_latest_log(self.project)

    def test_invalid_project(self):
        with self.assertRaises(FileNotFoundError):
            select_latest_log(self.root / 'NotThere.uproject')

    def test_cli_project_generates_local_report(self):
        self.make_log('ChickenFight.log',
                      'LogChickenCollision: PostPush Count=1\n'
                      'LogChickenMovement: MovementUpdate Velocity=(0,0,100)\n'
                      'LogTemp: Warning: sample warning\n', 1600000000)
        output = self.root / 'out'
        self.assertEqual(main(['--project', str(self.project), '--out', str(output)]), 0)
        info = json.loads((output / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(info['events']['PostPush'], 1)
        self.assertEqual(info['events']['MovementUpdate'], 1)
        self.assertEqual(info['counts']['warning'], 1)
        self.assertEqual(len(info['gameplay_samples']), 2)
        self.assertIn('Velocity', info['gameplay_samples'][1]['text'])
        self.assertEqual(info['counts']['test_passed'], 0)
        self.assertIn('Saved/Logs/ChickenFight.log', (output / 'report.md').read_text(encoding='utf-8'))

    def test_gameplay_sample_limit(self):
        logfile = self.make_log('ChickenFight.log',
                                ''.join(f'LogChickenCollision: PostPush Count={i}\n' for i in range(20)),
                                1600000000)
        summary = analyze_file(logfile)
        self.assertEqual(summary['events']['PostPush'], 20)
        self.assertEqual(len(summary['gameplay_samples']), 5)

    def test_crash_stack_context_and_redaction(self):
        logfile = self.make_log('ChickenFight.log',
                                'LoginId: SECRET_ID\n'
                                'Unhandled Exception: EXCEPTION_ACCESS_VIOLATION reading address 0xffffffffffffffff\n'
                                'UnrealEditor_DKUEndGame!AChickenCharacter::~AChickenCharacter()\n'
                                'C:\\Users\\PlayerName\\Desktop\\DKU\\Game.cpp:24\n', 1600000000)
        summary = analyze_file(logfile)
        self.assertEqual(summary['counts']['crash'], 1)
        self.assertEqual(len(summary['crash_contexts']), 1)
        joined = json.dumps(summary, ensure_ascii=False)
        self.assertIn('AChickenCharacter', joined)
        self.assertNotIn('PlayerName', joined)
        self.assertNotIn('SECRET_ID', joined)


if __name__ == '__main__':
    unittest.main()
