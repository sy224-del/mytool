import cv2
import numpy as np
import pyautogui
import sys
import termios
import tty
import time
import matplotlib.pyplot as plt
from pynput import mouse, keyboard
from threading import Timer, Thread
import queue
import json
import os
from datetime import datetime


# 1文字だけキーボード入力を取得する（Enter不要）
def getch():
    """1文字読み込み（Enter不要）"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


# 文字列入力を取得する（Enterで確定）
def get_string_input(prompt="入力してください: "):
    """文字列入力を取得（Enterで確定）"""
    print(prompt, end="", flush=True)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        # カノニカルモードを無効化
        tty.setraw(fd)

        input_string = ""
        while True:
            ch = sys.stdin.read(1)

            # Enterキーで確定
            if ch == "\r" or ch == "\n":
                print()  # 改行
                break
            # Backspaceキーで削除
            elif ch == "\x7f" or ch == "\x08":  # Backspace
                if input_string:
                    input_string = input_string[:-1]
                    # カーソルを1文字戻して空白で上書き
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            # 通常の文字
            else:
                input_string += ch
                sys.stdout.write(ch)
                sys.stdout.flush()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return input_string


# 現在の画面全体をキャプチャして画像として返す
def capture_screen():
    print("[INFO] 画面をキャプチャ中...")
    screen_width, screen_height = pyautogui.size()
    print(f"[INFO] 画面サイズ: {screen_width} x {screen_height}")
    screenshot = pyautogui.screenshot()
    image = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    image = cv2.resize(image, (screen_width, screen_height))
    print("[INFO] キャプチャ完了")
    return image


class ClickDetector:
    def __init__(self, recording_manager=None):
        self.last_click_time = 0
        self.last_click_pos = None
        self.double_click_threshold = 0.5  # ダブルクリック判定の時間閾値（秒）
        self.long_press_threshold = 1.0  # 長押し判定の時間閾値（秒）
        self.press_start_time = 0
        self.is_pressing = False
        self.long_press_timer = None
        self.recording_manager = recording_manager

    def on_click(self, x, y, button, pressed):
        current_time = time.time()

        if pressed:
            # クリック開始
            self.press_start_time = current_time
            self.is_pressing = True

            # 長押しタイマーを開始
            self.long_press_timer = Timer(
                self.long_press_threshold, self.on_long_press, args=[x, y]
            )
            self.long_press_timer.start()

            print(f"[MOUSE] クリック開始: x={x}, y={y}", end="\n\r")

            # 記録コールバックを呼び出し
            if self.recording_manager:
                self.recording_manager.add_action(
                    {
                        "type": "mouse_press",
                        "x": x,
                        "y": y,
                        "button": str(button),
                        "timestamp": current_time,
                    }
                )

        else:
            # クリック終了q
            self.is_pressing = False

            # 長押しタイマーをキャンセル
            if self.long_press_timer:
                self.long_press_timer.cancel()

            press_duration = current_time - self.press_start_time

            # 短いクリックの場合
            if press_duration < self.long_press_threshold:
                print(
                    f"[MOUSE] クリック終了: x={x}, y={y}, 押下時間: {press_duration:.2f}秒",
                    end="\n\r",
                )

                # 記録コールバックを呼び出し
                if self.recording_manager:
                    self.recording_manager.add_action(
                        {
                            "type": "mouse_release",
                            "x": x,
                            "y": y,
                            "button": str(button),
                            "duration": press_duration,
                            "timestamp": current_time,
                        }
                    )

                # ダブルクリック判定
                if (
                    self.last_click_pos == (x, y)
                    and current_time - self.last_click_time
                    < self.double_click_threshold
                ):
                    print(f"[MOUSE] ダブルクリック検出: x={x}, y={y}", end="\n\r")

                    # 前の4つのマウス操作を削除（mouse_press, mouse_release, mouse_press, mouse_release）
                    if self.recording_manager:
                        self.recording_manager.remove_last_actions(4)

                    # 記録コールバックを呼び出し
                    if self.recording_manager:
                        self.recording_manager.add_action(
                            {
                                "type": "mouse_double_click",
                                "x": x,
                                "y": y,
                                "timestamp": current_time,
                            }
                        )

                    self.last_click_time = 0  # リセット
                    self.last_click_pos = None
                else:
                    self.last_click_time = current_time
                    self.last_click_pos = (x, y)

    def on_long_press(self, x, y):
        """長押し検出時の処理"""
        if self.is_pressing:
            print(f"[MOUSE] 長押し検出: x={x}, y={y}", end="\n\r")

            # 記録コールバックを呼び出し
            if self.recording_manager:
                self.recording_manager.add_action(
                    {
                        "type": "mouse_long_press",
                        "x": x,
                        "y": y,
                        "timestamp": time.time(),
                    }
                )

            self.is_pressing = False


class KeyboardDetector:
    def __init__(self, recording_manager=None):
        self.pressed_keys = set()  # 現在押されているキーのセット
        self.key_combinations = {
            frozenset(["ctrl", "c"]): "コピー",
            frozenset(["ctrl", "v"]): "ペースト",
            frozenset(["ctrl", "z"]): "元に戻す",
            frozenset(["ctrl", "y"]): "やり直し",
            frozenset(["ctrl", "a"]): "全選択",
            frozenset(["ctrl", "s"]): "保存",
            frozenset(["ctrl", "f"]): "検索",
            frozenset(["alt", "tab"]): "アプリ切り替え",
            frozenset(["ctrl", "alt", "delete"]): "タスクマネージャー",
            frozenset(["windows", "d"]): "デスクトップ表示",
            frozenset(["windows", "e"]): "エクスプローラー",
            frozenset(["windows", "r"]): "ファイル名を指定して実行",
            frozenset(["ctrl", "shift", "esc"]): "タスクマネージャー（直接）",
            frozenset(["ctrl", "cmd", "f"]): "ウィンドウを拡大と縮小",
        }
        self.recording_manager = recording_manager

    def on_key_press(self, key):
        """キーが押された時の処理"""
        try:
            # キー名を取得
            key_name = self.get_key_name(key)
            if key_name:
                self.pressed_keys.add(key_name)
                print(f"[KEYBOARD] キー押下: {key_name}", end="\n\r")

                # 記録コールバックを呼び出し
                if self.recording_manager:
                    self.recording_manager.add_action(
                        {"type": "key_press", "key": key_name, "timestamp": time.time()}
                    )

                # 同時押しの組み合わせをチェック
                self.check_key_combinations()

        except AttributeError:
            print(f"[KEYBOARD] 特殊キー押下: {key}", end="\n\r")

            # 記録コールバックを呼び出し
            if self.recording_manager:
                self.recording_manager.add_action(
                    {"type": "key_press", "key": str(key), "timestamp": time.time()}
                )

    def on_key_release(self, key):
        """キーが離された時の処理"""
        try:
            key_name = self.get_key_name(key)
            if key_name and key_name in self.pressed_keys:
                self.pressed_keys.discard(key_name)
                print(f"[KEYBOARD] キー離上: {key_name}", end="\n\r")

                # 記録コールバックを呼び出し
                if self.recording_manager:
                    self.recording_manager.add_action(
                        {
                            "type": "key_release",
                            "key": key_name,
                            "timestamp": time.time(),
                        }
                    )

        except AttributeError:
            print(f"[KEYBOARD] 特殊キー離上: {key}", end="\n\r")

            # 記録コールバックを呼び出し
            if self.recording_manager:
                self.recording_manager.add_action(
                    {"type": "key_release", "key": str(key), "timestamp": time.time()}
                )

    def get_key_name(self, key):
        """キーオブジェクトからキー名を取得"""
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        elif hasattr(key, "name"):
            return key.name.lower()
        return None

    def check_key_combinations(self):
        """同時押しの組み合わせをチェック"""
        if len(self.pressed_keys) >= 2:
            key_set = frozenset(self.pressed_keys)
            if key_set in self.key_combinations:
                print(
                    f"[KEYBOARD] 同時押し検出: {' + '.join(self.pressed_keys)} → {self.key_combinations[key_set]}",
                    end="\n\r",
                )

                # 記録コールバックを呼び出し
                if self.recording_manager:
                    self.recording_manager.add_action(
                        {
                            "type": "key_combination",
                            "keys": list(self.pressed_keys),
                            "action": self.key_combinations[key_set],
                            "timestamp": time.time(),
                        }
                    )

    def get_current_keys(self):
        """現在押されているキーを取得"""
        return list(self.pressed_keys)

    def add_key_combination(self, keys, description):
        """新しいキーの組み合わせを追加"""
        if isinstance(keys, list):
            key_set = frozenset(keys)
            self.key_combinations[key_set] = description
            print(
                f"[KEYBOARD] 新しい組み合わせを追加: {' + '.join(keys)} → {description}",
                end="\n\r",
            )


class RecordingManager:
    def __init__(self):
        self.is_recording = False
        self.recorded_actions = []
        self.recording_start_time = None
        # 記録しない制御キーのリスト
        self.control_keys = {"s", "w", "q", "h", "k"}
        # ファイル名入力中かどうかのフラグ
        self.is_inputting_filename = False

    def start_recording(self):
        """記録を開始"""
        self.is_recording = True
        self.recorded_actions = []
        self.recording_start_time = time.time()
        print("[RECORD] 記録を開始しました")

    def stop_recording(self):
        """記録を停止"""
        self.is_recording = False
        print(
            f"[RECORD] 記録を停止しました。{len(self.recorded_actions)}個の操作を記録しました"
        )

    def add_action(self, action):
        """操作を記録"""
        if not self.is_recording:
            return

        # キーボード操作の場合、制御キーをチェック
        if action.get("type") in ["key_press", "key_release"]:
            key = action.get("key", "")

            # 制御キーの場合は記録しない
            if key in self.control_keys:
                return

            # ファイル名入力中の場合は記録しない
            if self.is_inputting_filename:
                return

        # 相対時間を計算
        if self.recording_start_time:
            action["relative_time"] = action["timestamp"] - self.recording_start_time
        self.recorded_actions.append(action)

    def set_inputting_filename(self, is_inputting):
        """ファイル名入力中のフラグを設定"""
        self.is_inputting_filename = is_inputting

    def remove_last_actions(self, count):
        """最後の指定された数の操作を削除"""
        if len(self.recorded_actions) >= count:
            removed_actions = self.recorded_actions[-count:]
            self.recorded_actions = self.recorded_actions[:-count]
            print(f"[RECORD] 最後の{count}個の操作を削除しました", end="\n\r")
            return removed_actions
        return []

    def save_to_json(self, filename=None):
        """記録された操作をJSONファイルに保存"""
        if not self.recorded_actions:
            print("[ERROR] 保存する操作がありません")
            return None

        # records フォルダを作成（存在しない場合）
        records_dir = os.path.join(os.path.dirname(__file__), "..", "records")
        os.makedirs(records_dir, exist_ok=True)

        if not filename:
            # ファイル名入力中フラグを設定
            self.set_inputting_filename(True)

            # ユーザーにファイル名を入力してもらう
            print("[SAVE] ファイル名を入力してください（拡張子なし）:")
            user_filename = get_string_input("ファイル名: ")

            # ファイル名入力中フラグを解除
            self.set_inputting_filename(False)

            if not user_filename.strip():
                # 空の場合はデフォルト名を使用
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recorded_actions_{timestamp}.json"
                print(f"[SAVE] デフォルト名を使用: {filename}")
            else:
                # ユーザー入力に.jsonを追加
                filename = f"{user_filename.strip()}.json"
                print(f"[SAVE] ファイル名: {filename}")

        # 保存パスを records フォルダに設定
        filepath = os.path.join(records_dir, filename)

        # 記録データを整理
        recording_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_actions": len(self.recorded_actions),
                "recording_duration": (
                    self.recorded_actions[-1]["relative_time"]
                    if self.recorded_actions
                    else 0
                ),
            },
            "actions": self.recorded_actions,
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(recording_data, f, ensure_ascii=False, indent=2)
            print(f"[RECORD] 操作を {filepath} に保存しました")
            return filepath
        except Exception as e:
            print(f"[ERROR] ファイル保存に失敗しました: {e}")
            return None

def print_help():
    """ヘルプメッセージを表示"""
    print("\n" + "=" * 50)
    print("PC自動化ツール - 操作ガイド")
    print("=" * 50)
    print("s: 保存モード開始/停止")
    print("w: 記録された操作をJSONファイルに保存")
    print("k: 現在押されているキーを表示")
    print("h: このヘルプを表示")
    print("q: プログラム終了")
    print("=" * 50)
    print("マウスとキーボードの操作が自動検知されます")
    print("保存モード中は操作が記録されます")
    print("ファイル保存時は自分で名前を付けられます")
    print("=" * 50 + "\n")


# メイン処理：キー入力受付、画面キャプチャ、領域検出、マウス座標取得
def main():
    print_help()

    # 記録マネージャーを初期化
    recording_manager = RecordingManager()

    # 検出器を初期化（記録コールバックを設定）
    click_detector = ClickDetector(recording_manager=recording_manager)
    keyboard_detector = KeyboardDetector(recording_manager=recording_manager)

    # キーボードリスナーを開始
    keyboard_listener = keyboard.Listener(
        on_press=keyboard_detector.on_key_press,
        on_release=keyboard_detector.on_key_release,
    )
    keyboard_listener.start()

    # マウスリスナーを開始
    mouse_listener = mouse.Listener(on_click=click_detector.on_click)
    mouse_listener.start()

    print("[INFO] 監視を開始しました。操作を検知します...")

    while True:
        try:
            key = getch()

            if key == "s":
                if recording_manager.is_recording:
                    recording_manager.stop_recording()
                else:
                    recording_manager.start_recording()
                print("[INFO] 次の操作を待機中...")

            elif key == "w":
                if recording_manager.recorded_actions:
                    filename = recording_manager.save_to_json()
                    if filename:
                        print(f"[INFO] ファイル保存完了: {filename}")
                else:
                    print("[INFO] 保存する操作がありません")
                print("[INFO] 次の操作を待機中...")

            elif key == "q":
                print("[INFO] プログラムを終了します...")
                break

            elif key == "k":
                # 現在押されているキーを表示
                current_keys = keyboard_detector.get_current_keys()
                if current_keys:
                    print(f"[INFO] 現在押されているキー: {', '.join(current_keys)}")
                else:
                    print("[INFO] 現在押されているキーはありません")
                print("[INFO] 次の操作を待機中...")

            elif key == "h":
                print_help()

            else:
                print(f"[INFO] 不明なキー: {key}")
                print("[INFO] 次の操作を待機中...")

        except KeyboardInterrupt:
            print("[INFO] Ctrl+Cで終了します...")
            break
        except Exception as e:
            print(f"[ERROR] エラーが発生しました: {e}")
            continue

    # リスナーを停止
    keyboard_listener.stop()
    mouse_listener.stop()
    print("[INFO] 監視を停止しました。")
