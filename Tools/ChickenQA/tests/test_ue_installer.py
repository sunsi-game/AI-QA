import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from chickenqa.ue_installer import locate_target, render_cpp, install_tests, InstallError
from chickenqa.test_report import read_unreal_report


class UnrealInstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        # .uproject file name deliberately differs from C++ module name.
        self.project = self.base / 'ChickenFight.uproject'
        self.project.write_text(json.dumps({'Modules': [{'Name': 'DKUEndGame', 'Type': 'Runtime'}]}), encoding='utf-8')
        self.module = self.base / 'Source' / 'DKUEndGame'
        self.module.mkdir(parents=True)
        (self.module / 'DKUEndGame.Build.cs').write_text('// stub', encoding='utf-8')
        self.header = self.module / 'Public' / 'ChickenCharacter.h'
        self.header.parent.mkdir()
        self.header.write_text('UCLASS()\nclass DKUENDGAME_API AChickenCharacter : public ACharacter\n{', encoding='utf-8')

    def test_detect_real_module_not_project_filename(self):
        target = locate_target(self.project)
        self.assertEqual(target.module, 'DKUEndGame')
        self.assertEqual(target.header, self.header)
        self.assertIn('/Script/DKUEndGame.ChickenCharacter', render_cpp(target))
        self.assertIn('WITH_DEV_AUTOMATION_TESTS', render_cpp(target))
        self.assertEqual(render_cpp(target).count('IMPLEMENT_SIMPLE_AUTOMATION_TEST('), 3)

    def test_dry_run_does_not_change_source(self):
        target = locate_target(self.project)
        message = install_tests(target, apply=False)
        self.assertIn('DRY RUN', message)
        self.assertFalse(target.cpp.exists())

    def test_apply_creates_new_cpp(self):
        target = locate_target(self.project)
        install_tests(target, apply=True)
        self.assertTrue(target.cpp.exists())
        self.assertIn('ClassRegistered', target.cpp.read_text(encoding='utf-8-sig'))

    def test_repeat_install_does_not_overwrite(self):
        target = locate_target(self.project)
        install_tests(target, apply=True)
        self.assertIn('unchanged', install_tests(target, apply=True))

    def test_refuse_overwrite_edited_source(self):
        target = locate_target(self.project)
        target.cpp.parent.mkdir(parents=True)
        target.cpp.write_text('// human-edited\n', encoding='utf-8')
        with self.assertRaises(InstallError):
            install_tests(target, apply=True)
        self.assertEqual(target.cpp.read_text(), '// human-edited\n')

    def test_no_character_class_fail_closed(self):
        self.header.write_text('class AOtherCharacter : public ACharacter {};', encoding='utf-8')
        with self.assertRaisesRegex(InstallError, 'declaration was not found'):
            locate_target(self.project)

    def test_module_constraint(self):
        with self.assertRaisesRegex(InstallError, 'not declared'):
            locate_target(self.project, 'UnrelatedModule')

    def test_absent_project_error(self):
        with self.assertRaises(InstallError):
            locate_target(self.base / 'Missing.uproject')

    def test_header_with_multiline_class_declaration(self):
        self.header.write_text('UCLASS()\nclass DKUENDGAME_API AChickenCharacter\n    : public ACharacter\n{', encoding='utf-8')
        self.assertEqual(locate_target(self.project).module, 'DKUEndGame')


class UnrealReportTests(unittest.TestCase):
    def test_report_parses_unreal_test_counts(self):
        with TemporaryDirectory() as folder:
            index = Path(folder) / 'index.json'
            index.write_text(json.dumps({'tests': [
                {'fullTestPath': 'ChickenQA.Character.ClassRegistered', 'state': 'Success'},
                {'fullTestPath': 'ChickenQA.Character.MovementComponentReady', 'state': 'Success'},
                {'fullTestPath': 'ChickenQA.Character.CapsuleConfigured', 'state': 'Success'},
            ]}), encoding='utf-8')
            result = read_unreal_report(index)
            self.assertEqual(result['total_tests'], 3)
            self.assertEqual(result['counts']['passed'], 3)


if __name__ == '__main__':
    unittest.main()
