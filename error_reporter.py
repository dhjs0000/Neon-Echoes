#!/usr/bin/env python3
"""
Neon Echoes - 错误报告模块

这个模块负责收集错误日志和系统信息，并在发生错误时提供用户友好的错误报告功能。
"""

import os
import sys
import zipfile
import shutil
import datetime
import platform
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger('NeonEchoes.ErrorReporter')
logger.setLevel(logging.INFO)

if logger.handlers:
    logger.handlers.clear()

log_file = os.path.join(os.path.dirname(__file__), 'logs', 'error_reporter_log.log')
file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class ErrorReporter:
    """错误报告类 - 负责收集和打包错误信息"""

    def __init__(self):
        """初始化错误报告器"""
        self.error_reports_dir = os.path.join(os.path.dirname(__file__), 'error_reports')
        self.logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
        self.project_root = os.path.dirname(__file__)

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        os.makedirs(self.error_reports_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            Dict[str, Any]: 系统信息字典
        """
        try:
            return {
                '操作系统': platform.system(),
                '操作系统版本': platform.version(),
                '操作系统架构': platform.machine(),
                'Python版本': platform.python_version(),
                'Python实现': platform.python_implementation(),
                '处理器': platform.processor(),
                '主机名': platform.node(),
                '当前时间': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"获取系统信息时出错: {e}")
            return {'错误': '无法获取系统信息'}

    def collect_logs(self) -> list:
        """
        收集所有日志文件
        
        Returns:
            list: 日志文件路径列表
        """
        log_files = []
        try:
            if os.path.exists(self.logs_dir):
                for file in os.listdir(self.logs_dir):
                    if file.endswith('.log'):
                        file_path = os.path.join(self.logs_dir, file)
                        if os.path.isfile(file_path):
                            log_files.append(file_path)
            logger.info(f"收集到 {len(log_files)} 个日志文件")
        except Exception as e:
            logger.error(f"收集日志文件时出错: {e}")
        return log_files

    def collect_project_info(self) -> Dict[str, Any]:
        """
        收集项目信息
        
        Returns:
            Dict[str, Any]: 项目信息字典
        """
        info = {
            '项目根目录': self.project_root
        }

        try:
            version_file = os.path.join(self.project_root, 'version.txt')
            if os.path.exists(version_file):
                with open(version_file, 'r', encoding='utf-8') as f:
                    info['版本'] = f.read().strip()
        except:
            pass

        return info

    def create_error_report(self, error_message: str, traceback_info: Optional[str] = None) -> Optional[str]:
        """
        创建错误报告并打包成zip文件
        
        Args:
            error_message (str): 错误消息
            traceback_info (Optional[str]): 堆栈跟踪信息
            
        Returns:
            Optional[str]: 错误报告文件路径，如果创建失败则返回None
        """
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"error_report_{timestamp}.zip"
            report_path = os.path.join(self.error_reports_dir, report_filename)

            with zipfile.ZipFile(report_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                system_info = self.get_system_info()

                system_info_text = "=== 系统信息 ===\n"
                for key, value in system_info.items():
                    system_info_text += f"{key}: {value}\n"

                if error_message:
                    system_info_text += f"\n=== 错误信息 ===\n{error_message}\n"

                if traceback_info:
                    system_info_text += f"\n=== 堆栈跟踪 ===\n{traceback_info}\n"

                zipf.writestr('system_info.txt', system_info_text)

                log_files = self.collect_logs()
                for log_file_path in log_files:
                    try:
                        arcname = os.path.join('logs', os.path.basename(log_file_path))
                        zipf.write(log_file_path, arcname)
                    except Exception as e:
                        logger.warning(f"无法添加日志文件 {log_file_path}: {e}")

                project_info = self.collect_project_info()
                project_info_text = "=== 项目信息 ===\n"
                for key, value in project_info.items():
                    project_info_text += f"{key}: {value}\n"
                zipf.writestr('project_info.txt', project_info_text)

                instructions = self.get_submission_instructions()
                zipf.writestr('SUBMISSION_INSTRUCTIONS.txt', instructions)

            logger.info(f"错误报告已创建: {report_path}")
            return report_path

        except Exception as e:
            logger.error(f"创建错误报告时出错: {e}")
            return None

    def get_submission_instructions(self) -> str:
        """
        获取错误提交说明
        
        Returns:
            str: 提交说明文本
        """
        return """=== 错误报告提交说明 ===

感谢您使用Neon Echoes并帮助我们改进游戏！

【提交错误的方法】

方法1：通过GitHub提交Issue（推荐）
1. 访问我们的GitHub仓库
2. 点击 "Issues" 标签
3. 点击 "New Issue" 按钮
4. 选择 "Bug report" 模板
5. 填写问题描述，包括：
   - 问题标题（简要描述问题）
   - 问题描述（详细说明问题）
   - 复现步骤
   - 预期行为和实际行为
6. 将此错误报告ZIP文件（包含logs文件夹中的日志）附加到Issue中

方法2：通过电子邮件提交
1. 编写邮件
2. 主题：TRG音游错误报告
3. 正文包括：
   - 问题描述
   - 复现步骤
   - 预期行为和实际行为
4. 将此错误报告ZIP文件作为附件
5. 发送到游戏开发者邮箱

【帮助我们更快解决问题】

请尽可能提供以下信息：
1. 发生错误时您在做什么
2. 错误消息内容
3. 操作系统版本
4. 终端类型（Windows Terminal, PowerShell, CMD等）
5. 是否有特定的谱面或操作导致错误

感谢您的反馈！
"""

    def get_user_instructions(self, report_path: str) -> str:
        """
        获取给用户的错误报告说明
        
        Args:
            report_path (str): 错误报告文件路径
            
        Returns:
            str: 用户说明文本
        """
        return f"""⚠️  发生错误！

错误报告已保存到: {report_path}

请按照以下步骤提交错误：

1. 访问GitHub仓库的Issues页面创建新的Bug report
2. 或发送邮件到游戏开发者邮箱
3. 将错误报告ZIP文件（包含logs文件夹中的日志）附加到您的报告中

详细信息请查看ZIP文件中的SUBMISSION_INSTRUCTIONS.txt

感谢您的反馈！
"""

    def clean_old_reports(self, max_reports: int = 10) -> int:
        """
        清理旧的错误报告文件
        
        Args:
            max_reports (int): 保留的最大报告数量
            
        Returns:
            int: 删除的报告数量
        """
        try:
            if not os.path.exists(self.error_reports_dir):
                return 0

            reports = sorted(
                [f for f in os.listdir(self.error_reports_dir) if f.startswith('error_report_') and f.endswith('.zip')],
                key=lambda x: os.path.getmtime(os.path.join(self.error_reports_dir, x))
            )

            deleted_count = 0
            while len(reports) > max_reports:
                old_report = reports.pop(0)
                report_path = os.path.join(self.error_reports_dir, old_report)
                try:
                    os.remove(report_path)
                    deleted_count += 1
                    logger.info(f"已删除旧错误报告: {old_report}")
                except Exception as e:
                    logger.warning(f"无法删除旧错误报告 {old_report}: {e}")

            return deleted_count

        except Exception as e:
            logger.error(f"清理旧错误报告时出错: {e}")
            return 0

    def get_reports_count(self) -> int:
        """
        获取错误报告数量
        
        Returns:
            int: 错误报告数量
        """
        try:
            if not os.path.exists(self.error_reports_dir):
                return 0
            return len([f for f in os.listdir(self.error_reports_dir) if f.startswith('error_report_') and f.endswith('.zip')])
        except:
            return 0
