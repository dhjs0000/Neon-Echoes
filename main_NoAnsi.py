#!/usr/bin/env python3
"""
Neon Echoes - 非ANSI版本主程序

这个模块是游戏的入口点，不使用ANSI转义序列进行渲染，
用于兼容不支持颜色的终端。
所有需要颜色识别的地方都使用视觉标识符来区分。
"""

# 版本号定义
__version__ = "0.2.0"

import sys
import os
import time
import select
import logging
import traceback
import datetime
import platform
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.excepthook = handle_startup_error

from save_manager import SaveManager

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game_engine import GameState, NoteType, Difficulty, JudgementResult
from noansi_renderer import NoAnsiRenderer
from audio_manager import AudioManager
from config_manager import ConfigManager
from chart_parser import get_available_charts, load_chart_by_id
from error_reporter import ErrorReporter


class NeonEchoesNoAnsi:
    """Neon Echoes非ANSI版本主游戏类"""

    def __init__(self):
        self.game_state = GameState(difficulty=Difficulty.NORMAL)

        self.config_manager = ConfigManager()
        self.settings = self.config_manager.load_config()

        self.renderer = NoAnsiRenderer(self.game_state)

        self.audio_manager = AudioManager()

        self.save_manager = SaveManager()

        self.is_paused = False
        self.game_running = False
        self.chart_loaded = False

        self.input_state = {
            'key_up': False,
            'key_down': False,
            'key_left': False,
            'key_right': False,
            'key_enter': False,
            'key_escape': False,
            'key_p': False,
            'key_delete': False,
        }

        self.menu_selection = 0
        self.menu_options = ["开始游戏", "设置", "退出游戏"]

        self.setting_options = [
            "音乐音量",
            "音效音量",
            "音乐延迟",
            "帧率设置",
            "AutoPlay",
            "调试计时器",
            "错误报告",
            "清空数据",
            "返回主菜单"
        ]

        self.chart_selection = 0
        self.charts = []
        self.current_page = 0
        self.charts_per_page = 5

        self.error_reporter = ErrorReporter()
        self.error_reporting_enabled = self.settings.get('错误报告', True)

        self.game_start_time = 0
        self.frame_count = 0
        self.last_frame_time = 0
        self.fps = 0
        self.frame_timings = []

        self.confirming_clear = False

        self.load_charts()

        self.setup_logging()

        self.logger.info("Neon Echoes NoAnsi 启动")

    def setup_logging(self) -> None:
        import logging
        self.logger = logging.getLogger('NeonEchoes.NoAnsi')
        self.logger.setLevel(logging.INFO)

        try:
            logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
            os.makedirs(logs_dir, exist_ok=True)

            file_handler = logging.FileHandler(
                os.path.join(logs_dir, 'noansi_game.log'),
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)

            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

        except Exception as e:
            print(f"无法设置日志: {e}")

    def load_charts(self) -> None:
        try:
            self.charts = get_available_charts()
            self.logger.info(f"加载了 {len(self.charts)} 个谱面")
        except Exception as e:
            self.logger.error(f"加载谱面列表时出错: {e}")
            self.charts = []

    def clear_screen(self) -> None:
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_input(self) -> Dict[str, bool]:
        keys = {k: False for k in self.input_state}

        if os.name != 'nt':
            return self._get_input_unix(keys)
        else:
            return self._get_input_windows(keys)

    def _get_input_unix(self, keys: Dict[str, bool]) -> Dict[str, bool]:
        try:
            if select.select([sys.stdin], [], [], 0.01)[0]:
                char = sys.stdin.read(1)
                if char == '\x1b':
                    seq = sys.stdin.read(2)
                    if seq == '[A':
                        keys['key_up'] = True
                    elif seq == '[B':
                        keys['key_down'] = True
                    elif seq == '[C':
                        keys['key_right'] = True
                    elif seq == '[D':
                        keys['key_left'] = True
                elif char == '\n':
                    keys['key_enter'] = True
                elif char == '\x7f':
                    keys['key_backspace'] = True
                elif char == 'p' or char == 'P':
                    keys['key_p'] = True
                elif char == '\x04':
                    keys['key_delete'] = True
        except:
            pass
        return keys

    def _get_input_windows(self, keys: Dict[str, bool]) -> Dict[str, bool]:
        try:
            import msvcrt
            if msvcrt.kbhit():
                char = msvcrt.getch()
                if char == b'\xe0':
                    arrow = msvcrt.getch()
                    if arrow == b'H':
                        keys['key_up'] = True
                    elif arrow == b'P':
                        keys['key_down'] = True
                    elif arrow == b'M':
                        keys['key_right'] = True
                    elif arrow == b'K':
                        keys['key_left'] = True
                elif char == b'\r':
                    keys['key_enter'] = True
                elif char == b'p' or char == b'P':
                    keys['key_p'] = True
                elif char == b'\x1b':
                    keys['key_escape'] = True
                elif char == b'\x03':
                    keys['key_delete'] = True
        except:
            pass
        return keys

    def handle_input(self, keys: Dict[str, bool]) -> None:
        if self.game_state.game_state == "MENU":
            self._handle_menu_input(keys)
        elif self.game_state.game_state == "SETTINGS":
            self._handle_settings_input(keys)
        elif self.game_state.game_state == "GAME":
            self._handle_game_input(keys)
        elif self.game_state.game_state == "RESULTS":
            self._handle_results_input(keys)
        elif self.game_state.game_state == "CHART_SELECT":
            self._handle_chart_select_input(keys)

    def _handle_menu_input(self, keys: Dict[str, bool]) -> None:
        if keys['key_up']:
            self.menu_selection = (self.menu_selection - 1) % len(self.menu_options)
            self.logger.debug(f"菜单选择: {self.menu_options[self.menu_selection]}")
        if keys['key_down']:
            self.menu_selection = (self.menu_selection + 1) % len(self.menu_options)
            self.logger.debug(f"菜单选择: {self.menu_options[self.menu_selection]}")
        if keys['key_enter']:
            self.logger.info(f"选择了菜单项: {self.menu_options[self.menu_selection]}")
            if self.menu_selection == 0:
                self.game_state.set_game_state("CHART_SELECT")
            elif self.menu_selection == 1:
                self.game_state.set_game_state("SETTINGS")
            elif self.menu_selection == 2:
                self.game_state.game_running = False

    def _handle_settings_input(self, keys: Dict[str, bool]) -> None:
        if keys['key_escape']:
            self.confirming_clear = False
            self.game_state.set_game_state("MENU")
            self.logger.info("返回主菜单")
        elif keys['key_up']:
            self.settings_selection = (self.settings_selection - 1) % len(self.setting_options)
        elif keys['key_down']:
            self.settings_selection = (self.settings_selection + 1) % len(self.setting_options)
        elif keys['key_enter']:
            self._handle_settings_action()
        elif keys['key_left'] or keys['key_right']:
            self._change_setting_value(keys['key_left'])
        elif self.confirming_clear and keys['key_enter']:
            if self.setting_options[self.settings_selection] == "清空数据":
                self.save_manager.clear_all_scores()
                self.logger.info("已清空所有成绩")
                self.confirming_clear = False

    def _handle_settings_action(self) -> None:
        current_option = self.setting_options[self.settings_selection]

        if current_option == "返回主菜单":
            self.confirming_clear = False
            self.game_state.set_game_state("MENU")
        elif current_option == "清空数据":
            self.confirming_clear = not self.confirming_clear
        else:
            self.confirming_clear = False

    def _change_setting_value(self, decreasing: bool) -> None:
        current_option = self.setting_options[self.settings_selection]
        delta = -1 if decreasing else 1

        if current_option == "音乐音量":
            new_volume = max(0, min(100, self.settings.get('音乐音量', 50) + delta * 5))
            self.settings['音乐音量'] = new_volume
            self.audio_manager.set_music_volume(new_volume / 100.0)
            self.config_manager.save_config(self.settings)
        elif current_option == "音效音量":
            new_volume = max(0, min(100, self.settings.get('音效音量', 50) + delta * 5))
            self.settings['音效音量'] = new_volume
            self.audio_manager.set_sfx_volume(new_volume / 100.0)
            self.config_manager.save_config(self.settings)
        elif current_option == "音乐延迟":
            new_delay = max(-200, min(200, self.settings.get('音乐延迟', 0) + delta * 10))
            self.settings['音乐延迟'] = new_delay
            self.config_manager.save_config(self.settings)
        elif current_option == "帧率设置":
            new_fps = max(30, min(144, self.settings.get('帧率设置', 60) + delta * 5))
            self.settings['帧率设置'] = new_fps
            self.config_manager.save_config(self.settings)
        elif current_option == "AutoPlay":
            new_autoplay = not self.settings.get('AutoPlay', False)
            self.settings['AutoPlay'] = new_autoplay
            self.config_manager.save_config(self.settings)
        elif current_option == "调试计时器":
            new_debug = not self.settings.get('调试计时器', False)
            self.settings['调试计时器'] = new_debug
            self.config_manager.save_config(self.settings)
        elif current_option == "错误报告":
            new_reporting = not self.settings.get('错误报告', True)
            self.settings['错误报告'] = new_reporting
            self.error_reporting_enabled = new_reporting
            self.config_manager.save_config(self.settings)

    def _handle_game_input(self, keys: Dict[str, bool]) -> None:
        if keys['key_escape']:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.audio_manager.pause_music()
            else:
                self.audio_manager.resume_music()

        if keys['key_p']:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.audio_manager.pause_music()
            else:
                self.audio_manager.resume_music()

        if not self.is_paused:
            autoplay = self.settings.get('AutoPlay', False)

            if not autoplay:
                for i, track in enumerate(self.game_state.tracks):
                    if i < len(self.game_state.track_keys):
                        if self._is_key_pressed(self.game_state.track_keys[i][0]) or self._is_key_pressed(self.game_state.track_keys[i][1]):
                            if not track.activated:
                                track.activated = True
                                self.game_state.combo = 0

            for i, track in enumerate(self.game_state.tracks):
                if i < len(self.game_state.track_keys):
                    if not self._is_key_pressed(self.game_state.track_keys[i][0]) and not self._is_key_pressed(self.game_state.track_keys[i][1]):
                        if track.activated:
                            track.activated = False

    def _is_key_pressed(self, key: str) -> bool:
        keys = self.get_input()
        key_map = {
            'd': 'key_d', 'f': 'key_f', 'j': 'key_j', 'k': 'key_k',
            'a': 'key_a', 's': 'key_s', '←': 'key_left', '→': 'key_right',
            '1': 'key_1', '2': 'key_2', '3': 'key_3', '4': 'key_4',
            '5': 'key_5', '6': 'key_6', '7': 'key_7', '8': 'key_8',
            '9': 'key_9', '0': 'key_0', '-': 'key_minus', '=': 'key_equals'
        }
        key_name = key_map.get(key.lower(), '')
        return keys.get(key_name, False)

    def _handle_results_input(self, keys: Dict[str, bool]) -> None:
        if keys['key_enter'] or keys['key_escape']:
            self.game_state.set_game_state("MENU")
            self.menu_selection = 0

    def _handle_chart_select_input(self, keys: Dict[str, bool]) -> None:
        if keys['key_escape']:
            self.game_state.set_game_state("MENU")

        if keys['key_up']:
            self.chart_selection = max(0, self.chart_selection - 1)
        if keys['key_down']:
            self.chart_selection = min(len(self.charts) - 1, self.chart_selection + 1)
        if keys['key_left']:
            self.current_page = max(0, self.current_page - 1)
        if keys['key_right']:
            max_page = (len(self.charts) - 1) // self.charts_per_page
            self.current_page = min(max_page, self.current_page + 1)
        if keys['key_enter']:
            if self.charts:
                chart = self.charts[self.chart_selection]
                self.start_game(chart['id'])

    def start_game(self, chart_id: str) -> None:
        try:
            chart = load_chart_by_id(chart_id)
            if chart:
                self.game_state.load_chart(chart)
                self.chart_loaded = True
                self.game_state.set_game_state("GAME")
                self.game_running = True
                self.is_paused = False
                self.game_start_time = time.time()
                self.audio_manager.load_music(chart['music_path'])
                self.audio_manager.play_music()
                self.logger.info(f"开始游戏: {chart['name']}")
        except Exception as e:
            self.logger.error(f"加载谱面失败: {e}")
            if self.error_reporting_enabled:
                self.error_reporter.report_error(f"加载谱面失败: {e}")

    def update(self) -> None:
        if not self.game_running or self.is_paused:
            return

        current_time = time.time()
        delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time

        self.frame_timings.append(delta_time)
        if len(self.frame_timings) > 60:
            self.frame_timings.pop(0)

        if self.frame_timings:
            avg_frame_time = sum(self.frame_timings) / len(self.frame_timings)
            self.fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0

        target_fps = self.settings.get('帧率设置', 60)
        frame_duration = 1.0 / target_fps

        time.sleep(max(0, frame_duration - delta_time))

        if self.chart_loaded:
            try:
                self.audio_manager.update()
            except Exception as e:
                self.logger.warning(f"音频更新时出错: {e}")

            try:
                self.game_state.update()
            except Exception as e:
                self.logger.warning(f"游戏状态更新时出错: {e}")

            autoplay = self.settings.get('AutoPlay', False)

            if autoplay:
                self._update_autoplay()

            if self.game_state.game_state == "RESULTS":
                self._handle_game_results()

    def _update_autoplay(self) -> None:
        current_time_ms = self.game_state.current_time_ms

        for track_idx, track in enumerate(self.game_state.tracks):
            for note in track.active_notes:
                if note.is_held and note.hold_completed:
                    continue

                note_time = note.time
                time_diff = note_time - current_time_ms

                if -50 <= time_diff <= 50:
                    if not track.activated:
                        track.activated = True
                elif time_diff < -100:
                    if track.activated:
                        track.activated = False

    def _handle_game_results(self) -> None:
        self.game_running = False
        self.chart_loaded = False
        self.audio_manager.stop_music()

        self.save_manager.save_score(
            self.game_state.chart_id,
            self.game_state.score,
            self.game_state.max_combo,
            self.game_state.perfect_count,
            self.game_state.great_count,
            self.game_state.good_count,
            self.game_state.bad_count,
            self.game_state.miss_count
        )

        self.game_state.set_game_state("RESULTS")

    def render(self) -> str:
        if self.game_state.game_state == "MENU":
            return self.renderer.draw_title_screen(self.game_state.ascii_art)
        elif self.game_state.game_state == "SETTINGS":
            values = {
                "音乐音量": self.settings.get('音乐音量', 50),
                "音效音量": self.settings.get('音效音量', 50),
                "音乐延迟": self.settings.get('音乐延迟', 0),
                "帧率设置": self.settings.get('帧率设置', 60),
                "AutoPlay": self.settings.get('AutoPlay', False),
                "调试计时器": self.settings.get('调试计时器', False),
                "错误报告": self.settings.get('错误报告', True),
            }
            return self.renderer.draw_settings_screen(self.setting_options, self.settings_selection, values)
        elif self.game_state.game_state == "GAME":
            output = self.renderer.render()
            if self.is_paused:
                output += "\n" + self.renderer.draw_pause_screen()
            return output
        elif self.game_state.game_state == "RESULTS":
            chart = None
            for c in self.charts:
                if c['id'] == self.game_state.chart_id:
                    chart = c
                    break

            chart_name = chart['name'] if chart else "Unknown"
            difficulty = chart['difficulty'] if chart else "NORMAL"

            return self.renderer.draw_results_screen(
                self.game_state.score,
                self.game_state.max_combo,
                self.game_state.perfect_count,
                self.game_state.great_count,
                self.game_state.good_count,
                self.game_state.bad_count,
                self.game_state.miss_count,
                chart_name,
                difficulty
            )
        elif self.game_state.game_state == "CHART_SELECT":
            return self._draw_chart_select()
        return ""

    def _draw_chart_select(self) -> str:
        return self.renderer.draw_chart_select_screen(
            self.charts,
            self.chart_selection,
            self.current_page,
            self.charts_per_page
        )

    def run(self) -> None:
        self.settings_selection = 0

        try:
            self.logger.info(f"Neon Echoes NoAnsi 版本 {__version__} 启动")

            while self.game_running or self.game_state.game_state in ["MENU", "SETTINGS", "CHART_SELECT", "RESULTS"]:
                current_time = time.time()
                delta_time = current_time - self.last_frame_time
                self.last_frame_time = current_time

                self.frame_timings.append(delta_time)
                if len(self.frame_timings) > 60:
                    self.frame_timings.pop(0)

                if self.frame_timings:
                    avg_frame_time = sum(self.frame_timings) / len(self.frame_timings)
                    self.fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0

                target_fps = self.settings.get('帧率设置', 60)
                frame_duration = 1.0 / target_fps

                time.sleep(max(0, frame_duration - delta_time))

                keys = self.get_input()

                if not (self.is_paused and self.game_state.game_state == "GAME"):
                    self.handle_input(keys)

                if self.game_state.game_state == "GAME" and not self.is_paused:
                    self.update()

                try:
                    output = self.render()
                    self.clear_screen()
                    print(output)
                except Exception as e:
                    self.logger.error(f"渲染时出错: {e}")

            self.logger.info("Neon Echoes NoAnsi 结束")

        except KeyboardInterrupt:
            self.logger.info("用户中断 Neon Echoes")
            print("\nNeon Echoes 退出")
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            self.logger.error(f"游戏发生错误: {e}\n{error_msg}")

            if self.error_reporting_enabled:
                report_path = self.error_reporter.create_error_report(str(e), error_msg)
                if report_path:
                    print(f"\n错误报告已创建: {report_path}")
                    print("\n请将错误报告提交到GitHub Issues或发送邮件给开发者。")
                else:
                    print(f"\n游戏发生错误: {e}")
            else:
                print(f"\n游戏发生错误（错误报告已禁用），请查看日志文件: {e}")
        finally:
            self.logger.info("Neon Echoes 结束")

    def _handle_input(self, key: str) -> None:
        pass


def handle_startup_error(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    try:
        logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        error_log_path = os.path.join(logs_dir, 'startup_error.log')
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write(f"时间: {datetime.datetime.now()}\n")
            f.write(f"版本: {__version__}\n")
            f.write(f"错误类型: {exc_type.__name__}\n")
            f.write(f"错误信息: {exc_value}\n")
            f.write(f"堆栈跟踪:\n{error_msg}\n")

            f.write("\n=== 系统信息 ===\n")
            f.write(f"操作系统: {platform.system()} {platform.version()}\n")
            f.write(f"Python版本: {platform.python_version()}\n")
            f.write(f"工作目录: {os.getcwd()}\n")

        print(f"\n启动时发生错误！\n")
        print(f"错误类型: {exc_type.__name__}")
        print(f"错误信息: {exc_value}")
        print(f"\n错误详情已保存到: {error_log_path}")
        print(f"\n请查看错误日志并提交Bug报告。\n")

        print("=== 如何提交错误报告 ===")
        print("方法1：通过GitHub提交Issue")
        print("方法2：发送邮件到游戏开发者邮箱")
        print("详细说明请查看 error_log 文件\n")

    except Exception as e:
        print(f"无法创建错误报告: {e}")
        print(f"原始错误: {error_msg}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Neon Echoes - 终端下落式音游 (非ANSI版本)')
    parser.add_argument('--chart', type=str, help='直接加载指定的谱面ID')

    args = parser.parse_args()

    game = NeonEchoesNoAnsi()

    if args.chart:
        game.start_game(args.chart)

    game.run()
