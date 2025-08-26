# cli.py
import argparse
from core import record_core, replay_core

def main():
    parser = argparse.ArgumentParser(prog="mytool")
    subparsers = parser.add_subparsers(dest="command")

    # 記録用サブコマンド
    subparsers.add_parser("record", help="操作を記録")

    # 再生用サブコマンド
    replay_parser = subparsers.add_parser("replay", help="記録を再生")
    replay_parser.add_argument("file", help="再生するJSONファイル")

    args = parser.parse_args()

    if args.command == "record":
        record_core.main()
    elif args.command == "replay":
        replay_core.main(args.file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
