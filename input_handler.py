#!/usr/bin/env python3
"""
Neon Echoes - 多线程输入处理模块

将输入检测放到独立线程中，避免阻塞主线程的渲染
"""

import threading
import queue
import time
import logging
from typing import Optional, Set, Dict, Callable
from collections import deque

# 配置日志
logger = logging.getLogger('NeonEchoes.InputHandler')


class InputEvent:
    """输入事件类"""
    KEY_DOWN = 'down'
    KEY_UP = 'up'
    
    def __init__(self, event_type: str, key: str, timestamp: float):
        self.event_type = event_type
        self.key = key
        self.timestamp = timestamp


class ThreadedInputHandler:
    """多线程输入处理器"""
    
    def __init__(self, key_mapping: Dict[str, int], vk_keys_cache: Dict[str, int]):
        """
        初始化输入处理器
        
        Args:
            key_mapping: 按键到轨道索引的映射
            vk_keys_cache: VK键码缓存
        """
        self.key_mapping = key_mapping
        self.vk_keys_cache = vk_keys_cache
        
        # 线程安全的输入事件队列
        self.event_queue: queue.Queue[InputEvent] = queue.Queue()
        
        # 当前按下的键集合（线程安全）
        self._pressed_keys: Set[str] = set()
        self._pressed_keys_lock = threading.Lock()
        
        # 输入处理线程
        self._input_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 回调函数
        self.on_key_down: Optional[Callable[[str, int], None]] = None
        self.on_key_up: Optional[Callable[[str, int], None]] = None
        
        # 性能监控
        self._last_check_time = time.time()
        # 优化：降低轮询频率到120Hz（8.33ms间隔），减少CPU占用
        # 120Hz对于音游输入已经足够，500Hz会造成过多的系统调用开销
        self._check_interval = 0.0083  # 8.3ms检查间隔（约120Hz轮询率）
        self._menu_check_interval = 0.033  # 菜单状态下30Hz（33ms）足够
        self._current_interval = self._check_interval
        
        # 游戏状态感知
        self._game_state = 'menu'  # 'menu' 或 'gameplay'
        
        logger.info("ThreadedInputHandler 初始化完成")
    
    def start(self) -> None:
        """启动输入处理线程"""
        if self._running:
            return
        
        self._running = True
        self._input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self._input_thread.start()
        logger.info("输入处理线程已启动")
    
    def stop(self) -> None:
        """停止输入处理线程"""
        self._running = False
        if self._input_thread and self._input_thread.is_alive():
            self._input_thread.join(timeout=0.1)
        logger.info("输入处理线程已停止")
    
    def set_game_state(self, state: str) -> None:
        """
        设置游戏状态，动态调整轮询频率
        
        Args:
            state: 'menu' 或 'gameplay'
        """
        if state != self._game_state:
            self._game_state = state
            if state == 'gameplay':
                self._current_interval = self._check_interval  # 120Hz
                logger.debug("输入轮询切换到高频模式 (120Hz)")
            else:
                self._current_interval = self._menu_check_interval  # 30Hz
                logger.debug("输入轮询切换到低频模式 (30Hz)")
    
    def _input_loop(self) -> None:
        """输入处理主循环（在独立线程中运行）"""
        import msvcrt
        import ctypes
        
        user32 = ctypes.windll.user32
        
        # 记录每个键的最后状态
        key_states: Dict[str, bool] = {}
        
        while self._running:
            loop_start = time.time()
            
            # 检查新按键输入（非阻塞）
            while msvcrt.kbhit():
                try:
                    ch = msvcrt.getch()
                    key = None
                    
                    if ch in [b'\x00', b'\xe0']:
                        # 特殊键
                        special_key = msvcrt.getch()
                        # 将特殊键映射到对应的键码
                        special_keys = {
                            b'H': '\x1b[A',  # 上箭头
                            b'P': '\x1b[B',  # 下箭头
                            b'K': '\x1b[D',  # 左箭头
                            b'M': '\x1b[C',  # 右箭头
                            b'S': '\x7f',    # Delete键
                            b'G': '\x1b',    # ESC键
                            b'O': '\r',      # 回车键（小键盘）
                            b'I': '\t',      # Tab键
                            b';': '\x1b[2~', # Insert键
                            b'Q': '\x1b[5~', # Page Up键
                            b'R': '\x1b[6~', # Page Down键
                            b'k': '\x1b[H',  # Home键
                            b'm': '\x1b[F',  # End键
                        }
                        key = special_keys.get(special_key)
                    else:
                        # 普通键
                        try:
                            key = ch.decode('utf-8')
                        except UnicodeDecodeError:
                            key = ch.decode('latin-1')
                    
                    # 处理所有按键（包括映射过的和特殊键）
                    if key:
                        timestamp = time.time()
                        self.event_queue.put(InputEvent(InputEvent.KEY_DOWN, key, timestamp))
                        
                        # 只将映射过的键添加到pressed_keys
                        if key in self.key_mapping:
                            with self._pressed_keys_lock:
                                self._pressed_keys.add(key)
                            key_states[key] = True
                            
                            # 调用回调
                            if self.on_key_down:
                                track_index = self.key_mapping[key]
                                self.on_key_down(key, track_index)
                except Exception as e:
                    logger.error(f"处理键盘输入时出错: {e}")
            
            # 检查已按下键的释放状态
            with self._pressed_keys_lock:
                keys_to_check = list(self._pressed_keys)
            
            for key in keys_to_check:
                if key in self.vk_keys_cache:
                    # 检查键是否释放
                    is_pressed = (user32.GetAsyncKeyState(self.vk_keys_cache[key]) & 0x8000) != 0
                    
                    if not is_pressed and key_states.get(key, False):
                        # 键已释放
                        timestamp = time.time()
                        self.event_queue.put(InputEvent(InputEvent.KEY_UP, key, timestamp))
                        with self._pressed_keys_lock:
                            self._pressed_keys.discard(key)
                        key_states[key] = False
                        
                        # 调用回调
                        if self.on_key_up:
                            track_index = self.key_mapping[key]
                            self.on_key_up(key, track_index)
            
            # 控制轮询频率 - 使用动态间隔
            elapsed = time.time() - loop_start
            sleep_time = self._current_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def get_pressed_keys(self) -> Set[str]:
        """获取当前按下的键集合（线程安全）"""
        with self._pressed_keys_lock:
            return self._pressed_keys.copy()
    
    def process_events(self) -> None:
        """处理所有待处理的输入事件（在主线程中调用）"""
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get_nowait()
                # 事件已经在_input_loop中处理，这里可以添加额外的处理逻辑
            except queue.Empty:
                break
    
    def is_key_pressed(self, key: str) -> bool:
        """检查指定键是否被按下"""
        with self._pressed_keys_lock:
            return key in self._pressed_keys


class InputBuffer:
    """输入缓冲区 - 用于平滑输入处理"""
    
    def __init__(self, buffer_size: int = 10):
        self.buffer_size = buffer_size
        self.press_times: Dict[str, deque] = {}
        self.release_times: Dict[str, deque] = {}
    
    def record_press(self, key: str, timestamp: float) -> None:
        """记录按键按下时间"""
        if key not in self.press_times:
            self.press_times[key] = deque(maxlen=self.buffer_size)
        self.press_times[key].append(timestamp)
    
    def record_release(self, key: str, timestamp: float) -> None:
        """记录按键释放时间"""
        if key not in self.release_times:
            self.release_times[key] = deque(maxlen=self.buffer_size)
        self.release_times[key].append(timestamp)
    
    def get_press_count(self, key: str, time_window: float) -> int:
        """获取指定时间窗口内的按键次数"""
        if key not in self.press_times:
            return 0
        
        current_time = time.time()
        count = 0
        for press_time in self.press_times[key]:
            if current_time - press_time <= time_window:
                count += 1
        return count
