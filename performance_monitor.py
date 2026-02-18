#!/usr/bin/env python3
"""
Neon Echoes - 性能监控模块

用于实时监控游戏性能，包括帧率、帧时间、卡顿检测等
"""

import time
import logging
from typing import List, Dict, Optional
from collections import deque

# 配置日志
logger = logging.getLogger('NeonEchoes.Performance')


class PerformanceMonitor:
    """性能监控器 - 跟踪游戏性能指标"""
    
    def __init__(self, max_samples: int = 120):
        """
        初始化性能监控器
        
        Args:
            max_samples (int): 保留的最大样本数
        """
        self.max_samples = max_samples
        self.frame_times: deque[float] = deque(maxlen=max_samples)
        self.last_frame_time: float = 0.0
        self.last_update_time: float = time.time()
        
        # 卡顿检测阈值（毫秒）
        self.stutter_threshold_ms = 20.0  # 超过20ms认为是一次卡顿
        self.stutter_count = 0
        
        # 性能统计
        self.stats = {
            'fps': 0.0,
            'avg_frame_time_ms': 0.0,
            'min_frame_time_ms': 0.0,
            'max_frame_time_ms': 0.0,
            'stutter_percentage': 0.0,
        }
        
        logger.info("性能监控器初始化完成")
    
    def record_frame(self, frame_time: float) -> None:
        """
        记录一帧的时间
        
        Args:
            frame_time (float): 帧时间（秒）
        """
        self.frame_times.append(frame_time)
        self.last_frame_time = frame_time
        
        # 检测卡顿
        frame_time_ms = frame_time * 1000
        if frame_time_ms > self.stutter_threshold_ms:
            self.stutter_count += 1
        
        # 每60帧更新一次统计
        if len(self.frame_times) >= 60:
            self._update_stats()
    
    def _update_stats(self) -> None:
        """更新性能统计"""
        if not self.frame_times:
            return
        
        times_ms = [t * 1000 for t in self.frame_times]
        
        self.stats['fps'] = 1000.0 / (sum(times_ms) / len(times_ms))
        self.stats['avg_frame_time_ms'] = sum(times_ms) / len(times_ms)
        self.stats['min_frame_time_ms'] = min(times_ms)
        self.stats['max_frame_time_ms'] = max(times_ms)
        self.stats['stutter_percentage'] = (self.stutter_count / len(self.frame_times)) * 100
        
        # 重置卡顿计数
        self.stutter_count = 0
    
    def get_stats(self) -> Dict[str, float]:
        """获取当前性能统计"""
        return self.stats.copy()
    
    def get_formatted_stats(self) -> str:
        """获取格式化的性能统计字符串"""
        stats = self.get_stats()
        return (
            f"FPS: {stats['fps']:.1f} | "
            f"Avg: {stats['avg_frame_time_ms']:.2f}ms | "
            f"Min: {stats['min_frame_time_ms']:.2f}ms | "
            f"Max: {stats['max_frame_time_ms']:.2f}ms | "
            f"Stutter: {stats['stutter_percentage']:.1f}%"
        )
    
    def is_performance_ok(self) -> bool:
        """检查性能是否正常"""
        stats = self.get_stats()
        # 如果帧率低于30或卡顿率超过10%，认为性能不佳
        return stats['fps'] >= 30.0 and stats['stutter_percentage'] < 10.0
    
    def reset(self) -> None:
        """重置监控器"""
        self.frame_times.clear()
        self.stutter_count = 0
        self.stats = {
            'fps': 0.0,
            'avg_frame_time_ms': 0.0,
            'min_frame_time_ms': 0.0,
            'max_frame_time_ms': 0.0,
            'stutter_percentage': 0.0,
        }
        logger.info("性能监控器已重置")


class FrameRateLimiter:
    """帧率限制器 - 精确控制游戏帧率"""
    
    def __init__(self, target_fps: int = 60):
        """
        初始化帧率限制器
        
        Args:
            target_fps (int): 目标帧率
        """
        self.target_fps = target_fps
        self.target_frame_time = 1.0 / target_fps
        self.last_frame_time = time.time()
        
        # 性能监控
        self.monitor = PerformanceMonitor()
        
        logger.info(f"帧率限制器初始化完成，目标帧率: {target_fps} FPS")
    
    def set_target_fps(self, fps: int) -> None:
        """
        设置目标帧率
        
        Args:
            fps (int): 新的目标帧率
        """
        self.target_fps = fps
        self.target_frame_time = 1.0 / fps
        logger.info(f"目标帧率已更改为: {fps} FPS")
    
    def wait_for_next_frame(self) -> float:
        """
        等待下一帧，保持目标帧率
        
        Returns:
            float: 实际帧时间（秒）
        """
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        # 计算需要等待的时间
        sleep_time = self.target_frame_time - elapsed
        
        if sleep_time > 0:
            time.sleep(sleep_time)
        
        # 计算实际帧时间
        frame_end_time = time.time()
        actual_frame_time = frame_end_time - self.last_frame_time
        self.last_frame_time = frame_end_time
        
        # 记录性能数据
        self.monitor.record_frame(actual_frame_time)
        
        return actual_frame_time
    
    def get_performance_stats(self) -> Dict[str, float]:
        """获取性能统计"""
        return self.monitor.get_stats()
    
    def get_formatted_stats(self) -> str:
        """获取格式化的性能统计"""
        return self.monitor.get_formatted_stats()


# 全局性能监控器实例
_global_monitor: Optional[PerformanceMonitor] = None


def get_global_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def reset_global_monitor() -> None:
    """重置全局性能监控器"""
    global _global_monitor
    _global_monitor = PerformanceMonitor()
