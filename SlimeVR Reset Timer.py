import sys
import time
import threading
import json
import os
import psutil
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QLCDNumber
from pynput.keyboard import Key, Controller
from PyQt5.QtCore import pyqtSignal
import signal

class TimerShortcutApp(QWidget):
    exit_signal = pyqtSignal()
    shortcut_signal = pyqtSignal()
    update_display_signal = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.initUI()
        self.running = False
        self.keyboard = Controller()
        self.load_settings()

        # Connect signals to slots
        self.exit_signal.connect(self.handle_exit)
        self.shortcut_signal.connect(self.execute_shortcut)
        self.update_display_signal.connect(self.update_display)

        # Start monitoring threads
        self.monitor_steamvr_thread = threading.Thread(target=self.monitor_steamvr)
        self.monitor_steamvr_thread.daemon = True
        self.monitor_steamvr_thread.start()
        self.monitor_slimevr_thread = threading.Thread(target=self.monitor_slimevr)
        self.monitor_slimevr_thread.daemon = True
        self.monitor_slimevr_thread.start()

        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)

    def initUI(self):
        self.setWindowTitle('SlimeVR Reset Timer')
        self.setFixedSize(400, 400)

        layout = QVBoxLayout()

        # タイマー時間設定
        self.timer_label = QLabel('タイマー時間 (分):')
        layout.addWidget(self.timer_label)

        self.timer_spinbox = QSpinBox()
        self.timer_spinbox.setMinimum(1)
        self.timer_spinbox.setMaximum(1440)  # 最大24時間
        self.timer_spinbox.setValue(1)  # デフォルトは1分
        layout.addWidget(self.timer_spinbox)

        # ショートカットキー設定
        self.shortcut_label = QLabel('ショートカットキー:')
        layout.addWidget(self.shortcut_label)

        self.shortcut_keys = ['None','CTRL', 'ALT', 'SHIFT', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                              'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

        self.shortcut_combobox1 = QComboBox()
        self.shortcut_combobox1.addItems(self.shortcut_keys)
        self.shortcut_combobox1.setCurrentText('CTRL')
        layout.addWidget(self.shortcut_combobox1)

        self.shortcut_combobox2 = QComboBox()
        self.shortcut_combobox2.addItems(self.shortcut_keys)
        self.shortcut_combobox2.setCurrentText('ALT')
        layout.addWidget(self.shortcut_combobox2)

        self.shortcut_combobox3 = QComboBox()
        self.shortcut_combobox3.addItems(self.shortcut_keys)
        self.shortcut_combobox3.setCurrentText('SHIFT')
        layout.addWidget(self.shortcut_combobox3)

        self.shortcut_combobox4 = QComboBox()
        self.shortcut_combobox4.addItems(self.shortcut_keys)
        self.shortcut_combobox4.setCurrentText('U')
        layout.addWidget(self.shortcut_combobox4)

        # カウントダウン表示
        self.countdown_display = QLCDNumber()
        self.countdown_display.setDigitCount(5)  # MM:SS 表示
        layout.addWidget(self.countdown_display)

        # 開始ボタン
        self.start_button = QPushButton('スタート')
        self.start_button.clicked.connect(self.start_timer)
        layout.addWidget(self.start_button)

        # 停止ボタン
        self.stop_button = QPushButton('ストップ')
        self.stop_button.clicked.connect(self.stop_timer)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)

        # セーブボタン
        self.save_button = QPushButton('設定を保存')
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def start_timer(self):
        self.running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        timer_minutes = self.timer_spinbox.value()
        timer_thread = threading.Thread(target=self.run_timer, args=(timer_minutes,))
        timer_thread.daemon = True  # Set as daemon thread
        timer_thread.start()

    def stop_timer(self):
        self.running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def run_timer(self, minutes):
        total_seconds = minutes * 60
        while self.running:
            # タイマーのカウントダウン
            for remaining in range(total_seconds, 0, -1):
                if not self.running:
                    return
                minutes_remaining = remaining // 60
                seconds_remaining = remaining % 60
                self.update_display_signal.emit(minutes_remaining, seconds_remaining)
                time.sleep(1)

            # ショートカットキーの送信 (emit signal to execute shortcut)
            self.shortcut_signal.emit()

    def update_display(self, minutes_remaining, seconds_remaining):
        self.countdown_display.display(f"{minutes_remaining:02}:{seconds_remaining:02}")

    def execute_shortcut(self):
        keys = [self.shortcut_combobox1.currentText(),
                self.shortcut_combobox2.currentText(),
                self.shortcut_combobox3.currentText(),
                self.shortcut_combobox4.currentText()]

        pressed_keys = []
        for key in keys:
            if key == 'None':
                continue  # Skip this key
            elif key == 'CTRL':
                pressed_keys.append(Key.ctrl)
            elif key == 'ALT':
                pressed_keys.append(Key.alt)
            elif key == 'SHIFT':
                pressed_keys.append(Key.shift)
            else:
                pressed_keys.append(key.lower())

        if not pressed_keys:
            return  # No keys to press

        # Press the keys
        try:
            # Use context managers for modifier keys
            contexts = []
            for k in pressed_keys[:-1]:
                contexts.append(self.keyboard.pressed(k))

            # Enter all contexts
            for ctx in contexts:
                ctx.__enter__()

            # Press and release the last key
            self.keyboard.press(pressed_keys[-1])
            self.keyboard.release(pressed_keys[-1])

        finally:
            # Exit all contexts in reverse order
            for ctx in reversed(contexts):
                ctx.__exit__(None, None, None)

    def save_settings(self):
        settings = {
            'timer_minutes': self.timer_spinbox.value(),
            'shortcut_keys': [self.shortcut_combobox1.currentText(), self.shortcut_combobox2.currentText(),
                              self.shortcut_combobox3.currentText(), self.shortcut_combobox4.currentText()]
        }
        with open('settings.json', 'w') as f:
            json.dump(settings, f)

    def load_settings(self):
        if os.path.exists('settings.json'):
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                self.timer_spinbox.setValue(settings.get('timer_minutes', 1))
                shortcut_keys = settings.get('shortcut_keys', ['CTRL', 'ALT', 'SHIFT', 'U'])
                self.shortcut_combobox1.setCurrentText(shortcut_keys[0])
                self.shortcut_combobox2.setCurrentText(shortcut_keys[1])
                self.shortcut_combobox3.setCurrentText(shortcut_keys[2])
                self.shortcut_combobox4.setCurrentText(shortcut_keys[3])

    def monitor_steamvr(self):
        steamvr_was_running = False
        while True:
            steamvr_running = any(proc.name().lower() == 'vrmonitor.exe' for proc in psutil.process_iter())
            if steamvr_running:
                steamvr_was_running = True
            elif steamvr_was_running and not steamvr_running:
                self.exit_signal.emit()
                break
            time.sleep(5)

    def monitor_slimevr(self):
        slimevr_was_running = False
        while True:
            slimevr_running = any(proc.name().lower() == 'slimevr.exe' for proc in psutil.process_iter())
            if slimevr_running:
                slimevr_was_running = True
            elif slimevr_was_running and not slimevr_running:
                self.exit_signal.emit()
                break
            time.sleep(5)

    def handle_exit(self, signum=None, frame=None):
        self.running = False  # Stop the timer thread
        self.stop_timer()
        QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TimerShortcutApp()
    window.show()
    sys.exit(app.exec_())