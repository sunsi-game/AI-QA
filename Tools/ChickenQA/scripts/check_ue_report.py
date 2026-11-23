from __future__ import annotations
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chickenqa.test_report import read_unreal_report


def main() -> int:
    parser = argparse.ArgumentParser(description='Require a real, successful UE Automation JSON result')
    parser.add_argument('--report', type=Path, required=True, help='Unreal report directory or index.json')
    parser.add_argument('--prefix', default='ChickenQA.', help='Expected test namespace')
    parser.add_argument('--min-tests', type=int, default=3)
    args = parser.parse_args()
    if args.min_tests < 1:
        parser.error('--min-tests must be >= 1')
    try:
        result = read_unreal_report(args.report)
    except (OSError, ValueError) as exc:
        print(f'[ERROR] {exc}', file=sys.stderr)
        return 2
    matching = [item for item in result['details'] if item['name'].startswith(args.prefix)]
    counts = result['counts']
    for item in matching:
        print(f"[{item['state']}] {item['name']}")
    if len(matching) < args.min_tests:
        print(f'[FAIL] Expected at least {args.min_tests} tests under {args.prefix}, found {len(matching)}', file=sys.stderr)
        return 1
    if any(item['state'].lower().replace(' ', '') not in ('success', 'passed', 'succeeded') for item in matching):
        print('[FAIL] Some matching tests are failed, skipped, unknown or succeeded with warnings', file=sys.stderr)
        return 1
    if any(counts[k] for k in ('failed', 'warning', 'not_run', 'other')):
        print(f'[FAIL] Report contains non-passing tests: {counts}', file=sys.stderr)
        return 1
    print(f'[PASS] {len(matching)} ChickenQA tests completed successfully (coverage depends on the selected test suite).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
