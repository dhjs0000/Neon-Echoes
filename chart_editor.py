#!/usr/bin/env python3
"""
Neon Echoes - 制谱器

使用PySide6创建的制谱器，支持：
- 选择并播放音频文件
- 监听按键，自动添加tap音符（10个轨道对应10个按键）
- 实时谱面预览
- 保存谱面为.chart格式
"""

import os
import sys
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QTextEdit, QSplitter, QFrame, QMessageBox,
    QGroupBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QUrl
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QKeyEvent
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# 配置日志
logger = logging.getLogger('NeonEchoes.ChartEditor')
logger.setLevel(logging.INFO)
if logger.handlers:
    logger.handlers.clear()
log_file = os.path.join(os.path.dirname(__file__), 'logs', 'chart_editor.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)
file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 按键映射 - 10个轨道对应10个按键
TRACK_KEYS = [
    Qt.Key_Q, Qt.Key_W, Qt.Key_E, Qt.Key_R, Qt.Key_T,
    Qt.Key_Y, Qt.Key_U, Qt.Key_I, Qt.Key_O, Qt.Key_P
]

TRACK_KEY_LABELS = ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P']


class Note:
    """音符类"""

    def __init__(self, time_ms: int, track: int, note_type: str = "normal"):
        self.time_ms = time_ms
        self.track = track
        self.type = note_type
        self.duration = 0

    def to_chart_line(self) -> str:
        """转换为.chart格式的一行"""
        if self.type == "normal":
            return f"tab-{self.track + 1}"
        elif self.type == "hold":
            return f"hold-{self.track + 1}-{self.duration}"
        elif self.type == "drag":
            return f"drag-{self.track + 1}"
        return ""

    def __lt__(self, other):
        return self.time_ms < other.time_ms


class ChartPreviewWidget(QWidget):
    """谱面预览控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.notes: List[Note] = []
        self.current_time_ms = 0
        self.num_tracks = 10
        self.setMinimumHeight(300)

    def set_notes(self, notes: List[Note]):
        self.notes = notes
        self.update()

    def set_current_time(self, time_ms: int):
        self.current_time_ms = time_ms
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 20, 30))

        width = self.width()
        height = self.height()
        track_width = width / self.num_tracks
        center_y = height // 2
        preview_duration = 5000

        # 绘制轨道
        for i in range(self.num_tracks):
            x = int(i * track_width)
            color = QColor(60, 60, 80)
            painter.fillRect(x, 0, int(track_width), height, color)

            # 轨道边界
            pen = QPen(QColor(80, 80, 100), 1)
            painter.setPen(pen)
            painter.drawLine(x, 0, x, height)

        # 绘制判定线
        pen = QPen(QColor(255, 50, 50), 2)
        painter.setPen(pen)
        painter.drawLine(0, center_y, width, center_y)

        # 绘制音符
        for note in self.notes:
            time_diff = note.time_ms - self.current_time_ms
            if abs(time_diff) > preview_duration:
                continue

            track_x = int(note.track * track_width)
            note_width = int(track_width * 0.8)
            note_x = track_x + int(track_width * 0.1)

            # 计算Y位置
            progress = time_diff / preview_duration
            note_y = center_y - int(progress * (center_y - 30))

            if 0 <= note_y < height - 10:
                if note.type == "normal":
                    color = QColor(50, 200, 50)
                elif note.type == "hold":
                    color = QColor(50, 50, 200)
                elif note.type == "drag":
                    color = QColor(200, 200, 50)
                else:
                    color = QColor(200, 200, 200)

                painter.fillRect(note_x, note_y, note_width, 15, color)
                pen = QPen(QColor(255, 255, 255), 1)
                painter.setPen(pen)
                painter.drawRect(note_x, note_y, note_width, 15)

        # 绘制轨道标签
        painter.setPen(QColor(200, 200, 200))
        font = QFont("Arial", 10)
        painter.setFont(font)
        for i in range(self.num_tracks):
            x = int(i * track_width + track_width // 2 - 5)
            painter.drawText(x, 20, TRACK_KEY_LABELS[i])


class ChartEditorWindow(QMainWindow):
    """制谱器主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neon Echoes - 制谱器")
        self.setGeometry(100, 100, 1200, 800)

        self.notes: List[Note] = []
        self.is_playing = False
        self.is_recording = False
        self.record_start_time = 0.0
        self.media_player: Optional[QMediaPlayer] = None
        self.audio_output: Optional[QAudioOutput] = None
        self.audio_file: Optional[str] = None

        self._setup_ui()
        self._setup_media_player()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_preview)
        self.update_timer.start(33)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 标题
        title_label = QLabel("🎵 Neon Echoes 制谱器 🎵")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00ffaa; padding: 10px;")
        main_layout.addWidget(title_label)

        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)

        # 顶部控制区
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)

        # 文件控制区
        file_group = QGroupBox("文件设置")
        file_layout = QHBoxLayout(file_group)

        self.audio_file_btn = QPushButton("选择音频文件")
        self.audio_file_btn.clicked.connect(self._select_audio_file)
        file_layout.addWidget(self.audio_file_btn)

        self.audio_file_label = QLabel("未选择音频文件")
        self.audio_file_label.setStyleSheet("color: #aaaaaa;")
        file_layout.addWidget(self.audio_file_label, 1)
        top_layout.addWidget(file_group)

        # 谱面信息区
        info_group = QGroupBox("谱面信息")
        info_layout = QHBoxLayout(info_group)

        info_layout.addWidget(QLabel("曲名:"))
        self.name_edit = QLineEdit("新谱面")
        info_layout.addWidget(self.name_edit)

        info_layout.addWidget(QLabel("作者:"))
        self.maker_edit = QLineEdit("Unknown")
        info_layout.addWidget(self.maker_edit)

        info_layout.addWidget(QLabel("难度等级:"))
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 20)
        self.level_spin.setValue(5)
        info_layout.addWidget(self.level_spin)

        info_layout.addWidget(QLabel("难度:"))
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["EZ", "HD", "IN", "AT", "SP"])
        self.difficulty_combo.setCurrentIndex(1)
        info_layout.addWidget(self.difficulty_combo)

        info_layout.addWidget(QLabel("速度:"))
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 30.0)
        self.speed_spin.setValue(5.0)
        self.speed_spin.setSingleStep(0.5)
        info_layout.addWidget(self.speed_spin)

        top_layout.addWidget(info_group)

        # 播放控制区
        play_group = QGroupBox("播放控制")
        play_layout = QHBoxLayout(play_group)

        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.clicked.connect(self._toggle_play)
        self.play_btn.setMinimumHeight(40)
        self.play_btn.setStyleSheet("background-color: #336633; font-size: 14px;")
        play_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setMinimumHeight(40)
        play_layout.addWidget(self.stop_btn)

        play_layout.addWidget(QLabel("|"))

        self.record_btn = QPushButton("🎤 录制")
        self.record_btn.clicked.connect(self._toggle_record)
        self.record_btn.setMinimumHeight(40)
        self.record_btn.setStyleSheet("background-color: #663333; font-size: 14px;")
        play_layout.addWidget(self.record_btn)

        self.clear_btn = QPushButton("🗑️ 清空音符")
        self.clear_btn.clicked.connect(self._clear_notes)
        self.clear_btn.setMinimumHeight(40)
        play_layout.addWidget(self.clear_btn)

        play_layout.addWidget(QLabel("|"))

        self.save_btn = QPushButton("💾 保存谱面")
        self.save_btn.clicked.connect(self._save_chart)
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("background-color: #333366; font-size: 14px;")
        play_layout.addWidget(self.save_btn)

        top_layout.addWidget(play_group)

        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("进度:"))
        self.time_label = QLabel("0:00.000 / 0:00.000")
        progress_layout.addWidget(self.time_label)
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderPressed.connect(self._slider_pressed)
        self.progress_slider.sliderReleased.connect(self._slider_released)
        self.progress_slider.sliderMoved.connect(self._slider_moved)
        progress_layout.addWidget(self.progress_slider, 1)
        top_layout.addLayout(progress_layout)

        splitter.addWidget(top_widget)

        # 预览区
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        preview_label = QLabel("谱面预览 (使用 Q W E R T Y U I O P 添加音符)")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setStyleSheet("font-size: 14px; color: #aaaaaa; padding: 5px;")
        preview_layout.addWidget(preview_label)

        self.preview_widget = ChartPreviewWidget()
        preview_layout.addWidget(self.preview_widget, 1)

        # 音符列表
        notes_label = QLabel("音符列表:")
        notes_label.setStyleSheet("font-size: 14px; color: #aaaaaa; padding: 5px;")
        preview_layout.addWidget(notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setMaximumHeight(150)
        self.notes_text.setStyleSheet("background-color: #111111; color: #00ffaa; font-family: monospace;")
        preview_layout.addWidget(self.notes_text)

        splitter.addWidget(preview_widget)
        splitter.setSizes([300, 500])

    def _setup_media_player(self):
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)

    def _select_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "", "音频文件 (*.mp3 *.wav *.ogg *.flac)"
        )
        if file_path:
            self.audio_file = file_path
            self.audio_file_label.setText(Path(file_path).name)
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            logger.info(f"选择了音频文件: {file_path}")

    def _toggle_play(self):
        if not self.audio_file:
            QMessageBox.warning(self, "警告", "请先选择音频文件！")
            return

        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _stop(self):
        self.media_player.stop()
        self.is_recording = False
        self.record_btn.setText("🎤 录制")
        self.record_btn.setStyleSheet("background-color: #663333; font-size: 14px;")

    def _toggle_record(self):
        if not self.audio_file:
            QMessageBox.warning(self, "警告", "请先选择音频文件！")
            return

        self.is_recording = not self.is_recording
        if self.is_recording:
            self.record_start_time = time.time()
            self.record_btn.setText("⏹ 停止录制")
            self.record_btn.setStyleSheet("background-color: #ff3333; font-size: 14px;")
            if self.media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.play()
        else:
            self.record_btn.setText("🎤 录制")
            self.record_btn.setStyleSheet("background-color: #663333; font-size: 14px;")

    def _clear_notes(self):
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有音符吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.notes.clear()
            self._update_notes_text()
            self.preview_widget.set_notes(self.notes)

    def _save_chart(self):
        if not self.notes:
            QMessageBox.warning(self, "警告", "谱面没有音符！")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存谱面", "", "谱面文件 (*.chart)"
        )
        if file_path:
            self._write_chart(file_path)

    def _write_chart(self, file_path: str):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"name-{self.name_edit.text()}\n")
                f.write(f"maker-{self.maker_edit.text()}\n")
                f.write(f"level-{self.level_spin.value()}-{self.difficulty_combo.currentText()}\n")
                if self.audio_file:
                    f.write(f"audio-{Path(self.audio_file).name}\n")
                else:
                    f.write("audio-N\n")
                f.write(f"speed-{self.speed_spin.value()}\n\n")

                sorted_notes = sorted(self.notes)
                current_time_str = ""

                for note in sorted_notes:
                    time_str = self._format_time(note.time_ms)
                    if time_str != current_time_str:
                        current_time_str = time_str
                        f.write(f"{time_str}\n")
                    f.write(f"{note.to_chart_line()}\n")

                f.write("\n&\n")

            QMessageBox.information(self, "成功", f"谱面已保存到:\n{file_path}")
            logger.info(f"谱面已保存到: {file_path}")
        except Exception as e:
            logger.error(f"保存谱面失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")

    def _format_time(self, ms: int) -> str:
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        millis = ms % 1000
        return f"{minutes}:{seconds}:{millis:03d}"

    def _update_preview(self):
        if self.media_player:
            position = self.media_player.position()
            self.preview_widget.set_current_time(position)
            self.preview_widget.set_notes(self.notes)

    def _on_position_changed(self, position: int):
        duration = self.media_player.duration()
        if duration > 0:
            self.progress_slider.setValue(int(position * 1000 / duration))

        pos_str = self._format_time(position)
        dur_str = self._format_time(duration)
        self.time_label.setText(f"{pos_str} / {dur_str}")

    def _on_duration_changed(self, duration: int):
        pass

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸ 暂停")
            self.play_btn.setStyleSheet("background-color: #666633; font-size: 14px;")
        else:
            self.play_btn.setText("▶ 播放")
            self.play_btn.setStyleSheet("background-color: #336633; font-size: 14px;")

    def _slider_pressed(self):
        self.media_player.pause()

    def _slider_released(self):
        value = self.progress_slider.value()
        duration = self.media_player.duration()
        if duration > 0:
            position = int(value * duration / 1000)
            self.media_player.setPosition(position)
        self.media_player.play()

    def _slider_moved(self, value):
        duration = self.media_player.duration()
        if duration > 0:
            position = int(value * duration / 1000)
            pos_str = self._format_time(position)
            dur_str = self._format_time(duration)
            self.time_label.setText(f"{pos_str} / {dur_str}")

    def _update_notes_text(self):
        sorted_notes = sorted(self.notes)
        text = ""
        for i, note in enumerate(sorted_notes[-50:], max(0, len(sorted_notes) - 50) + 1):
            time_str = self._format_time(note.time_ms)
            text += f"{i:3d}. [{time_str}] 轨道 {note.track + 1} ({TRACK_KEY_LABELS[note.track]})\n"
        self.notes_text.setText(text)
        self.notes_text.verticalScrollBar().setValue(self.notes_text.verticalScrollBar().maximum())

    def keyPressEvent(self, event: QKeyEvent):
        if not self.is_recording:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key in TRACK_KEYS:
            track_index = TRACK_KEYS.index(key)
            position = self.media_player.position()
            note = Note(position, track_index, "normal")
            self.notes.append(note)
            self._update_notes_text()
            logger.debug(f"添加音符: 轨道 {track_index + 1}, 时间 {position}ms")

        super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ChartEditorWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
