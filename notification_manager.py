#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多通道通知管理器 - 智能新闻工作台
吸收 TrendRadar 的多渠道推送概念，提供灵活的通知分发：
1. Console - 控制台输出
2. File - 日志文件记录
3. Email - 邮件推送 (SMTP)
4. Webhook - HTTP回调推送
5. Desktop - 桌面通知 (可选 plyer)
"""

import os
import json
import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict, field
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class NotificationMessage:
    """通知消息数据类"""
    title: str
    content: str
    level: str = "info"  # info, warning, critical
    timestamp: str = ""
    source: str = "system"  # system, opinion_monitor, news_filter
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class NotificationChannel:
    """通知通道基类"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    def send(self, message: NotificationMessage) -> bool:
        """发送通知，由子类实现"""
        raise NotImplementedError

    def __repr__(self):
        return f"<Channel:{self.name} enabled={self.enabled}>"


class ConsoleChannel(NotificationChannel):
    """控制台通道"""

    def __init__(self):
        super().__init__("console", enabled=True)

    def send(self, message: NotificationMessage) -> bool:
        level_tag = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨"
        }.get(message.level, "📢")
        msg = f"[{message.timestamp}] {level_tag} [{message.source}] {message.title}: {message.content[:200]}"
        if message.level == "critical":
            logger.critical(msg)
        elif message.level == "warning":
            logger.warning(msg)
        else:
            logger.info(msg)
        return True


class FileChannel(NotificationChannel):
    """文件日志通道"""

    def __init__(self, log_dir: str = "notification_logs"):
        super().__init__("file", enabled=True)
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._log_file = os.path.join(log_dir, f"notifications_{datetime.now().strftime('%Y%m')}.jsonl")

    def send(self, message: NotificationMessage) -> bool:
        try:
            data = asdict(message)
            data["_received_at"] = datetime.now().isoformat()
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            logger.error(f"FileChannel写入失败: {e}")
            return False

    def get_recent(self, limit: int = 50, level: Optional[str] = None) -> List[Dict]:
        """获取最近的推送记录"""
        records = []
        if not os.path.exists(self._log_file):
            return records

        try:
            with open(self._log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            if level and record.get("level") != level:
                                continue
                            records.append(record)
                        except json.JSONDecodeError:
                            continue

            return records[-limit:]
        except Exception as e:
            logger.error(f"读取通知记录失败: {e}")
            return []


class EmailChannel(NotificationChannel):
    """邮件推送通道"""

    def __init__(self):
        super().__init__("email", enabled=False)
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.qq.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.to_addr = os.getenv("NOTIFY_EMAIL", "")
        self.use_ssl = os.getenv("SMTP_SSL", "true").lower() == "true"

        if self.smtp_user and self.smtp_pass and self.to_addr:
            self.enabled = True
            logger.info(f"邮件通道已启用: {self.smtp_user} -> {self.to_addr}")

    def send(self, message: NotificationMessage) -> bool:
        if not self.enabled:
            logger.debug("邮件通道未启用，跳过")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = self.to_addr
            msg["Subject"] = f"[{message.level.upper()}] {message.title}"

            body = f"""
            <html>
            <body style="font-family: 'Microsoft YaHei', sans-serif; padding: 20px;">
                <h2 style="color: {'#ef4444' if message.level == 'critical' else '#f59e0b' if message.level == 'warning' else '#3b82f6'};">
                    {'🚨 ' if message.level == 'critical' else '⚠️ ' if message.level == 'warning' else 'ℹ️ '}
                    {message.title}
                </h2>
                <div style="color: #374151; line-height: 1.6; margin: 16px 0;">
                    {message.content.replace(chr(10), '<br>')}
                </div>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 16px 0;">
                <div style="color: #9ca3af; font-size: 12px;">
                    <p>来源: {message.source}</p>
                    <p>时间: {message.timestamp}</p>
                    {f'<p>其他信息: {json.dumps(message.meta, ensure_ascii=False)}</p>' if message.meta else ''}
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(body, "html", "utf-8"))

            if self.use_ssl:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)

            logger.info(f"邮件推送成功: {message.title[:50]}")
            return True

        except Exception as e:
            logger.error(f"邮件推送失败: {e}")
            return False


class WebhookChannel(NotificationChannel):
    """Webhook HTTP回调通道"""

    def __init__(self):
        super().__init__("webhook", enabled=False)
        self.webhook_url = os.getenv("WEBHOOK_URL", "")
        self.webhook_headers = {}
        extra_headers = os.getenv("WEBHOOK_HEADERS", "")
        if extra_headers:
            try:
                self.webhook_headers = json.loads(extra_headers)
            except json.JSONDecodeError:
                pass

        if self.webhook_url:
            self.enabled = True
            logger.info(f"Webhook通道已启用: {self.webhook_url[:60]}...")

    def send(self, message: NotificationMessage) -> bool:
        if not self.enabled:
            return False

        try:
            import requests
            payload = asdict(message)
            payload["_sent_at"] = datetime.now().isoformat()

            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    **self.webhook_headers
                },
                timeout=10
            )
            if resp.ok:
                logger.info(f"Webhook推送成功: {message.title[:50]}")
                return True
            else:
                logger.warning(f"Webhook返回非200: {resp.status_code}")
                return False

        except ImportError:
            logger.warning("需要安装requests库才能使用Webhook通道: pip install requests")
            return False
        except Exception as e:
            logger.error(f"Webhook推送失败: {e}")
            return False


class DesktopChannel(NotificationChannel):
    """桌面通知通道"""

    def __init__(self):
        super().__init__("desktop", enabled=True)

    def send(self, message: NotificationMessage) -> bool:
        try:
            # 尝试使用 plyer
            try:
                from plyer import notification
                notification.notify(
                    title=message.title,
                    message=message.content[:200],
                    timeout=5,
                )
                return True
            except ImportError:
                pass

            # 备用: 使用 Windows Toast
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    message.title,
                    message.content[:200],
                    duration=5,
                    threaded=True
                )
                return True
            except ImportError:
                pass

            # 都不行就fallback到console
            logger.info(f"[桌面通知] {message.title}: {message.content[:100]}")
            return True

        except Exception as e:
            logger.warning(f"桌面通知失败: {e}")
            return False


class NotificationManager:
    """通知管理器 - 统一管理多通道通知"""

    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self._history: List[NotificationMessage] = []
        self._max_history = 200
        self._lock = threading.Lock()

        # 注册默认通道
        self._register_default_channels()

    def _register_default_channels(self):
        """注册默认通道"""
        self.register_channel(ConsoleChannel())
        self.register_channel(FileChannel())
        self.register_channel(EmailChannel())
        self.register_channel(WebhookChannel())
        self.register_channel(DesktopChannel())

    def register_channel(self, channel: NotificationChannel):
        """注册通知通道"""
        self.channels[channel.name] = channel
        logger.debug(f"注册通知通道: {channel.name} (启用={channel.enabled})")

    def unregister_channel(self, name: str):
        """注销通知通道"""
        if name in self.channels:
            del self.channels[name]
            logger.debug(f"注销通知通道: {name}")

    def send_notification(self, message: NotificationMessage,
                          channels: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        发送通知到指定通道

        Args:
            message: 通知消息
            channels: 通道名称列表，None表示所有已启用通道

        Returns:
            Dict[str, bool]: 各通道的发送结果
        """
        results = {}

        target_channels = channels or list(self.channels.keys())

        with self._lock:
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        for name in target_channels:
            channel = self.channels.get(name)
            if channel and channel.enabled:
                try:
                    success = channel.send(message)
                    results[name] = success
                except Exception as e:
                    logger.error(f"通道[{name}]发送失败: {e}")
                    results[name] = False
            else:
                results[name] = False

        return results

    def send_alert(self, title: str, content: str, level: str = "info",
                   source: str = "system", meta: Optional[Dict] = None,
                   channels: Optional[List[str]] = None) -> Dict[str, bool]:
        """快捷发送告警通知"""
        message = NotificationMessage(
            title=title,
            content=content,
            level=level,
            source=source,
            meta=meta or {}
        )
        return self.send_notification(message, channels=channels)

    def get_history(self, limit: int = 50, level: Optional[str] = None,
                    source: Optional[str] = None) -> List[NotificationMessage]:
        """获取通知历史"""
        with self._lock:
            results = list(self._history)

        if level:
            results = [m for m in results if m.level == level]
        if source:
            results = [m for m in results if m.source == source]

        return results[-limit:]

    def get_channel_status(self) -> Dict[str, Dict]:
        """获取各通道状态"""
        status = {}
        for name, channel in self.channels.items():
            status[name] = {
                "enabled": channel.enabled,
                "type": channel.__class__.__name__
            }
        return status

    def get_file_channel(self) -> Optional[FileChannel]:
        """获取文件通道实例"""
        channel = self.channels.get("file")
        if isinstance(channel, FileChannel):
            return channel
        return None


# 全局实例
_manager_instance = None


def get_notification_manager():
    """获取通知管理器实例（单例模式）"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = NotificationManager()
    return _manager_instance


if __name__ == "__main__":
    # 测试代码
    manager = get_notification_manager()

    print("=" * 60)
    print("多通道通知管理器测试")
    print("=" * 60)

    # 发送测试通知
    results = manager.send_alert(
        title="测试通知",
        content="这是一条来自智能新闻工作台的测试通知消息。",
        level="info",
        source="test"
    )
    print(f"通知发送结果: {results}")

    # 发送告警级别通知
    results = manager.send_alert(
        title="舆情异常告警",
        content="检测到舆情异常：某话题情感值在1小时内下降30%。",
        level="warning",
        source="opinion_monitor",
        meta={"topic": "AI监管", "drop_rate": "30%"}
    )
    print(f"告警发送结果: {results}")

    # 查看通道状态
    print("\n通道状态:")
    for name, status in manager.get_channel_status().items():
        print(f"  {name}: {'✅ 启用' if status['enabled'] else '❌ 禁用'} ({status['type']})")

    # 查看历史
    print(f"\n通知历史: {len(manager.get_history())} 条")
