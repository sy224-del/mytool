from cgi import test
import json
import time
import pyautogui
import sys
import termios
import tty
from pynput import mouse, keyboard
from datetime import datetime
import argparse


# 1文字だけキーボード入力を取得する（Enter不要）
def getch():
    """1文字読み込み（Enter不要）"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    except:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


class ActionPlayer:
    def __init__(self):
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        self.is_playing = False
        self.current_action_index = 0
        self.total_actions = 0

    def load_actions(self, filename):
        """JSONファイルから操作を読み込み"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.actions = data.get("actions", [])
            self.metadata = data.get("metadata", {})
            self.total_actions = len(self.actions)

            print(f"[LOAD] ファイル読み込み完了: {filename}")
            print(f"[LOAD] 操作数: {self.total_actions}")
            print(
                f"[LOAD] 記録時間: {self.metadata.get('recording_duration', 0):.2f}秒"
            )
            print(f"[LOAD] 作成日時: {self.metadata.get('created_at', '不明')}")

            return True

        except FileNotFoundError:
            print(f"[ERROR] ファイルが見つかりません: {filename}")
            return False
        except json.JSONDecodeError:
            print(f"[ERROR] JSONファイルの形式が正しくありません: {filename}")
            return False
        except Exception as e:
            print(f"[ERROR] ファイル読み込みエラー: {e}")
            return False

    def play_action(self, action):
        """単一の操作を実行"""
        action_type = action.get("type")

        try:
            if action_type == "mouse_press":
                x, y = action.get("x"), action.get("y")
                button = self._parse_button(action.get("button"))
                self.mouse_controller.position = (x, y)
                self.mouse_controller.press(button)
                print(f"[PLAY] マウス押下: ({x}, {y}) - {button}")

            elif action_type == "mouse_release":
                x, y = action.get("x"), action.get("y")
                button = self._parse_button(action.get("button"))
                self.mouse_controller.position = (x, y)
                self.mouse_controller.release(button)
                print(f"[PLAY] マウス離上: ({x}, {y}) - {button}")

            elif action_type == "mouse_double_click":
                x, y = action.get("x"), action.get("y")
                self.mouse_controller.position = (x, y)
                time.sleep(0.05)
                # ダブルクリックを実装（clickを2回呼び出し）
                self.mouse_controller.click(mouse.Button.left, count=2)
                print(f"[PLAY] ダブルクリック: ({x}, {y})")

            elif action_type == "mouse_long_press":
                x, y = action.get("x"), action.get("y")
                self.mouse_controller.position = (x, y)
                self.mouse_controller.press(mouse.Button.left)
                time.sleep(1.0)  # 長押しを再現
                self.mouse_controller.release(mouse.Button.left)
                print(f"[PLAY] 長押し: ({x}, {y})")

            elif action_type == "key_press":
                key = action.get("key")
                key_obj = self._parse_key(key)
                if key_obj:
                    self.keyboard_controller.press(key_obj)
                    print(f"[PLAY] キー押下: {key}")

            elif action_type == "key_release":
                key = action.get("key")
                key_obj = self._parse_key(key)
                if key_obj:
                    self.keyboard_controller.release(key_obj)
                    print(f"[PLAY] キー離上: {key}")

            elif action_type == "key_combination":
                keys = action.get("keys", [])
                action_name = action.get("action", "")
                for key in keys:
                    key_obj = self._parse_key(key)
                    if key_obj:
                        self.keyboard_controller.press(key_obj)
                time.sleep(0.1)  # 少し待機
                for key in reversed(keys):  # 逆順で離上
                    key_obj = self._parse_key(key)
                    if key_obj:
                        self.keyboard_controller.release(key_obj)
                print(f"[PLAY] 同時押し: {' + '.join(keys)} → {action_name}")

        except Exception as e:
            print(f"[ERROR] 操作実行エラー: {e}")

    def _parse_button(self, button_str):
        """ボタン文字列をボタンオブジェクトに変換"""
        if "left" in button_str.lower():
            return mouse.Button.left
        elif "right" in button_str.lower():
            return mouse.Button.right
        elif "middle" in button_str.lower():
            return mouse.Button.middle
        return mouse.Button.left

    def _parse_key(self, key_str):
        """キー文字列をキーオブジェクトに変換"""
        if not key_str:
            return None

        # 特殊キーの処理
        special_keys = {
            "ctrl": keyboard.Key.ctrl,
            "alt": keyboard.Key.alt,
            "shift": keyboard.Key.shift,
            "cmd": keyboard.Key.cmd,
            "windows": keyboard.Key.cmd,
            "enter": keyboard.Key.enter,
            "space": keyboard.Key.space,
            "tab": keyboard.Key.tab,
            "escape": keyboard.Key.esc,
            "esc": keyboard.Key.esc,
            "backspace": keyboard.Key.backspace,
            "delete": keyboard.Key.delete,
            "up": keyboard.Key.up,
            "down": keyboard.Key.down,
            "left": keyboard.Key.left,
            "right": keyboard.Key.right,
            "home": keyboard.Key.home,
            "end": keyboard.Key.end,
            "page_up": keyboard.Key.page_up,
            "page_down": keyboard.Key.page_down,
            "f1": keyboard.Key.f1,
            "f2": keyboard.Key.f2,
            "f3": keyboard.Key.f3,
            "f4": keyboard.Key.f4,
            "f5": keyboard.Key.f5,
            "f6": keyboard.Key.f6,
            "f7": keyboard.Key.f7,
            "f8": keyboard.Key.f8,
            "f9": keyboard.Key.f9,
            "f10": keyboard.Key.f10,
            "f11": keyboard.Key.f11,
            "f12": keyboard.Key.f12,
        }

        if key_str.lower() in special_keys:
            return special_keys[key_str.lower()]

        # 通常の文字キー
        if len(key_str) == 1:
            return key_str

        return None

    def play_all_actions(self, speed_multiplier=1.0):
        """すべての操作を再生"""
        if not self.actions:
            print("[ERROR] 再生する操作がありません")
            return

        self.is_playing = True
        self.current_action_index = 0

        print(f"[PLAY] 再生開始 (速度: {speed_multiplier}x)")
        print(f"[PLAY] 操作数: {self.total_actions}")

        start_time = time.time()

        for i, action in enumerate(self.actions):
            if not self.is_playing:
                print("[PLAY] 再生を停止しました")
                break

            self.current_action_index = i + 1

            # 操作を実行
            self.play_action(action)

            # 次の操作までの待機時間を計算
            if i < len(self.actions) - 1:
                current_relative_time = action.get("relative_time", 0)
                next_relative_time = self.actions[i + 1].get("relative_time", 0)
                wait_time = (
                    next_relative_time - current_relative_time
                ) / speed_multiplier

                if wait_time > 0:
                    time.sleep(wait_time)

        end_time = time.time()
        actual_duration = end_time - start_time

        print(f"[PLAY] 再生完了")
        print(f"[PLAY] 実際の再生時間: {actual_duration:.2f}秒")
        self.is_playing = False

    def stop_playback(self):
        """再生を停止"""
        self.is_playing = False
        print("[PLAY] 再生停止リクエスト")

    def preview_actions(self, max_actions=10):
        """操作のプレビューを表示"""
        if not self.actions:
            print("[ERROR] プレビューする操作がありません")
            return

        print(
            f"\n[PREVIEW] 操作プレビュー (最初の{min(max_actions, len(self.actions))}個):"
        )
        print("-" * 60)

        for i, action in enumerate(self.actions[:max_actions]):
            action_type = action.get("type")
            relative_time = action.get("relative_time", 0)

            if action_type.startswith("mouse"):
                x, y = action.get("x", 0), action.get("y", 0)
                print(f"{i+1:3d}. [{relative_time:6.2f}s] {action_type}: ({x}, {y})")
            elif action_type.startswith("key"):
                key = action.get("key", "")
                print(f"{i+1:3d}. [{relative_time:6.2f}s] {action_type}: {key}")

        if len(self.actions) > max_actions:
            print(f"... 他 {len(self.actions) - max_actions} 個の操作")


def print_help():
    """ヘルプメッセージを表示"""
    print("\n" + "=" * 60)
    print("PC操作再生ツール - 操作ガイド")
    print("=" * 60)
    print("p: 操作プレビュー表示")
    print("1: 通常速度で再生")
    print("2: 2倍速で再生")
    print("3: 3倍速で再生")
    print("s: 再生停止")
    print("h: このヘルプを表示")
    print("q: プログラム終了")
    print("=" * 60)
    print("再生中は操作が自動実行されます")
    print("注意: 再生前に適切なウィンドウをアクティブにしてください")
    print("=" * 60 + "\n")


# replay_core.py
def main(filename):
    # プレイヤーを初期化
    player = ActionPlayer()

    # ファイルを読み込み
    if not player.load_actions(filename):
        print("[ERROR] ファイルの読み込みに失敗しました")
        return

    print_help()
    player.preview_actions()
    print("[INFO] 再生準備完了。コマンドを入力してください...")

    while True:
        try:
            key = getch()
            if key == "p":
                player.preview_actions()
                print("[INFO] 次のコマンドを待機中...")

            elif key == "1":
                print("[INFO] 通常速度で再生開始...")
                player.play_all_actions(speed_multiplier=1.0)
                print("[INFO] 次のコマンドを待機中...")

            elif key == "2":
                print("[INFO] 2倍速で再生開始...")
                player.play_all_actions(speed_multiplier=2.0)
                print("[INFO] 次のコマンドを待機中...")

            elif key == "3":
                print("[INFO] 3倍速で再生開始...")
                player.play_all_actions(speed_multiplier=3.0)
                print("[INFO] 次のコマンドを待機中...")

            elif key == "s":
                player.stop_playback()
                print("[INFO] 再生停止リクエスト送信")
                print("[INFO] 次のコマンドを待機中...")

            elif key == "h":
                print_help()

            elif key == "q":
                print("[INFO] プログラムを終了します...")
                break

            else:
                print(f"[INFO] 不明なキー: {key}")
                print("[INFO] 次のコマンドを待機中...")

        except KeyboardInterrupt:
            print("\n[INFO] Ctrl+Cで終了します...")
            break
        except Exception as e:
            print(f"[ERROR] エラーが発生しました: {e}")
            continue
