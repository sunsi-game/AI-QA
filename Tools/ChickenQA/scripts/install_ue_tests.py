from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Run from any current directory, including PowerShell's ChickenQA directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chickenqa.ue_installer import InstallError, install_tests, locate_target


def main() -> int:
    parser = argparse.ArgumentParser(description='Install non-invasive ChickenQA Unreal C++ smoke tests')
    parser.add_argument('--project', type=Path, required=True, help='Absolute .uproject path')
    parser.add_argument('--module', help='Declared Unreal module name, only needed when ambiguous')
    parser.add_argument('--apply', action='store_true', help='Create the file (default is dry-run)')
    args = parser.parse_args()
    try:
        target = locate_target(args.project, args.module)
        print(f'[Project] {target.project}')
        print(f'[Module]  {target.module}')
        print(f'[Class]   {target.header}')
        print(install_tests(target, apply=args.apply))
        if args.apply:
            print('Next: close the Unreal Editor, compile the Editor target in Visual Studio, then run the automation suite.')
        return 0
    except (InstallError, OSError, UnicodeError) as exc:
        print(f'[ERROR] {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
