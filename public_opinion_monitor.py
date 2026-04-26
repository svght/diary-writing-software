#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
舆情异常检测系统 - 智能新闻工作台
吸收 TrendRadar 的信号检测和 Glance 的异常监控理念：
1. 情感异常检测 - 情感值突变
2. 热度异常检测 - 热度突然飙升/下降
3. 实体异常检测 - 实体出现频率突变
4. 话题异动检测 - 新话题快速崛起
5. 跨平台共振检测 - 多平台同时关注
"""

import os
import json
import time
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter

from notification_manager import get_notification_manager, NotificationMessage


@dataclass
class AnomalyAlert:
    """异常告警数据类"""
    type: str  # sentiment, hotness, entity, topic, cross_platform
    level: str  # info, warning, critical
    title: str
    description: str
    timestamp: str = ""
    source: str = "opinion_monitor"
    related_items: List[Dict] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class OpinionMonitor:
    """舆情异常检测器"""

    # 异常检测阈值
    THRESHOLDS = {
        "sentiment": {
            "drop_1h": 0.25,       # 1小时内情感值下降25%
            "drop_3h": 0.40,       # 3小时内下降40%
            "extreme_negative": 0.15,  # 极端负面占比超过15%
        },
        "hotness": {
            "surge_1h": 2.0,       # 1小时内热度翻倍
            "surge_3h": 3.0,       # 3小时内热度3倍
            "drop_1h": 0.5,        # 1小时内热度减半
        },
        "entity": {
            "frequency_surge": 3.0,  # 实体出现频率突增3倍
            "new_entity_threshold": 2,  # 新实体出现次数阈值
        },
        "topic": {
            "rise_speed": 5.0,      # 话题每小时的新闻量增长
            "min_news_count": 3,    # 最少新闻数
        },
        "cross_platform": {
            "min_platforms": 3,     # 最少跨平台数
            "min_news_count": 5,    # 最少总新闻数
        }
    }

    def __init__(self):
        # 历史数据缓存
        self._sentiment_history: Dict[str, List[Dict]] = defaultdict(list)
        self._hotness_history: Dict[str, List[float]] = defaultdict(list)
        self._entity_history: Dict[str, List[str]] = defaultdict(list)
        self._topic_history: Dict[str, List[float]] = defaultdict(list)

        # 告警记录
        self._alerts: List[AnomalyAlert] = []
        self._max_alerts = 200

        # 上次分析时间
        self._last_analysis_time = 0
        # 最小分析间隔(秒)
        self._min_interval = 300  # 5分钟

    def analyze(self, news_items: List[Dict[str, Any]],
                sentiment_data: Optional[Dict] = None,
                force: bool = False) -> List[AnomalyAlert]:
        """
        执行全维度舆情异常分析

        Args:
            news_items: 当前新闻条目列表
            sentiment_data: 情感分析数据（可选）
            force: 是否强制分析（跳过时间间隔检查）

        Returns:
            List[AnomalyAlert]: 发现的异常告警列表
        """
        current_time = time.time()

        # 检查最小分析间隔
        if not force and current_time - self._last_analysis_time < self._min_interval:
            return []

        self._last_analysis_time = current_time
        alerts = []

        # 更新历史数据
        self._update_history(news_items, sentiment_data)

        # 执行各项检测
        try:
            alerts.extend(self._detect_sentiment_anomalies(sentiment_data))
        except Exception as e:
            print(f"情感异常检测失败: {e}")

        try:
            alerts.extend(self._detect_hotness_anomalies(news_items))
        except Exception as e:
            print(f"热度异常检测失败: {e}")

        try:
            alerts.extend(self._detect_entity_anomalies(news_items))
        except Exception as e:
            print(f"实体异常检测失败: {e}")

        try:
            alerts.extend(self._detect_topic_anomalies(news_items))
        except Exception as e:
            print(f"话题异常检测失败: {e}")

        try:
            alerts.extend(self._detect_cross_platform_resonance(news_items))
        except Exception as e:
            print(f"跨平台共振检测失败: {e}")

        # 记录告警
        for alert in alerts:
            self._alerts.append(alert)
            if len(self._alerts) > self._max_alerts:
                self._alerts = self._alerts[-self._max_alerts:]

            # 触发通知
            try:
                notifier = get_notification_manager()
                notifier.send_alert(
                    title=alert.title,
                    content=alert.description,
                    level=alert.level,
                    source="opinion_monitor",
                    meta={
                        "type": alert.type,
                        "metrics": alert.metrics
                    }
                )
            except Exception as e:
                print(f"推送告警通知失败: {e}")

        return alerts

    def _update_history(self, news_items: List[Dict],
                        sentiment_data: Optional[Dict]):
        """更新历史数据"""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M")

        # 更新情感历史
        if sentiment_data:
            for key, value in sentiment_data.items():
                if isinstance(value, (int, float)):
                    self._sentiment_history[key].append({
                        "time": timestamp,
                        "value": value
                    })
                    # 保留最近24小时的数据
                    if len(self._sentiment_history[key]) > 288:
                        self._sentiment_history[key] = self._sentiment_history[key][-288:]

        # 更新热度历史
        for item in news_items:
            title = item.get('title', '') or ''
            hot_score = item.get('hot_score', 0) or 0
            if title and hot_score:
                self._hotness_history[title].append(hot_score)
                # 保留最近10个数据点
                if len(self._hotness_history[title]) > 10:
                    self._hotness_history[title] = self._hotness_history[title][-10:]

    def _detect_sentiment_anomalies(self, sentiment_data: Optional[Dict]) -> List[AnomalyAlert]:
        """检测情感异常"""
        alerts = []

        if not sentiment_data:
            return alerts

        # 检测极端负面
        negative_ratio = sentiment_data.get('negative_ratio', 0)
        if negative_ratio > self.THRESHOLDS["sentiment"]["extreme_negative"]:
            alerts.append(AnomalyAlert(
                type="sentiment",
                level="warning",
                title="舆情负面情绪偏高",
                description=f"当前新闻中负面情感占比达到 {negative_ratio*100:.1f}%"
                            f"，超过阈值 {self.THRESHOLDS['sentiment']['extreme_negative']*100:.0f}%",
                metrics={"negative_ratio": negative_ratio}
            ))

        # 检测情感突变（需要历史数据）
        positive_history = self._sentiment_history.get('positive_ratio', [])
        if len(positive_history) >= 6:  # 至少30分钟数据
            recent = [h['value'] for h in positive_history[-3:]]
            older = [h['value'] for h in positive_history[-6:-3]]

            if older and recent:
                avg_recent = sum(recent) / len(recent)
                avg_older = sum(older) / len(older)

                if avg_older > 0:
                    drop_rate = (avg_older - avg_recent) / avg_older
                    if drop_rate > self.THRESHOLDS["sentiment"]["drop_1h"]:
                        alerts.append(AnomalyAlert(
                            type="sentiment",
                            level="critical" if drop_rate > 0.4 else "warning",
                            title="舆情情感值异常下降",
                            description=f"正面情感比例在短期内从 {avg_older*100:.1f}%"
                                        f"下降至 {avg_recent*100:.1f}%，"
                                        f"降幅 {drop_rate*100:.1f}%",
                            metrics={
                                "drop_rate": drop_rate,
                                "avg_older": avg_older,
                                "avg_recent": avg_recent
                            }
                        ))

        return alerts

    def _detect_hotness_anomalies(self, news_items: List[Dict]) -> List[AnomalyAlert]:
        """检测热度异常"""
        alerts = []

        # 检测当前新闻中热度异常高的
        for item in news_items:
            title = item.get('title', '') or ''
            hot_score = item.get('hot_score', 0) or 0
            hot_scorers = item.get('hot_scorers', 0) or 0

            # 使用加权得分
            score = max(hot_score, hot_scorers)
            if score > 900:
                alerts.append(AnomalyAlert(
                    type="hotness",
                    level="warning",
                    title=f"新闻热度异常: {title[:40]}...",
                    description=f"该新闻热度评分高达 {score:.0f} 分，属于超高热话题",
                    related_items=[item],
                    metrics={"score": score}
                ))

        # 检测热度突变
        for title, history in self._hotness_history.items():
            if len(history) >= 4:
                recent = [h for h in history[-2:] if h]
                older = [h for h in history[-4:-2] if h]

                if recent and older:
                    avg_recent = sum(recent) / len(recent)
                    avg_older = sum(older) / len(older)

                    if avg_older > 0:
                        # 飙升检测
                        if avg_recent / avg_older > self.THRESHOLDS["hotness"]["surge_1h"]:
                            alerts.append(AnomalyAlert(
                                type="hotness",
                                level="warning",
                                title=f"热度飙升: {title[:40]}...",
                                description=f"热度从 {avg_older:.0f} 飙升至 {avg_recent:.0f}，"
                                            f"增长 {((avg_recent/avg_older)-1)*100:.0f}%",
                                metrics={
                                    "old_score": avg_older,
                                    "new_score": avg_recent,
                                    "ratio": avg_recent / avg_older
                                }
                            ))

        return alerts

    def _detect_entity_anomalies(self, news_items: List[Dict]) -> List[AnomalyAlert]:
        """检测实体异常"""
        alerts = []

        # 提取当前所有实体
        current_entities = Counter()
        for item in news_items:
            title = item.get('title', '') or ''
            content = item.get('content', '') or item.get('description', '') or ''
            text = f"{title} {content}"

            # 简单实体提取
            import re
            words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
            for w in words:
                # 过滤停用词
                if len(w) >= 2 and w not in self._STOP_WORDS:
                    current_entities[w] += 1

        # 检测新热点实体
        top_new_entities = current_entities.most_common(10)
        for entity, count in top_new_entities:
            if count >= self.THRESHOLDS["entity"]["new_entity_threshold"]:
                # 检查历史中是否有这个实体
                historical_count = 0
                for prev_entities in list(self._entity_history.values())[-5:]:
                    historical_count += prev_entities.count(entity)

                if historical_count == 0:
                    alerts.append(AnomalyAlert(
                        type="entity",
                        level="info",
                        title=f"新实体崛起: {entity}",
                        description=f"实体「{entity}」在短时间内出现 {count} 次，"
                                    f"可能成为新的热点话题",
                        metrics={
                            "entity": entity,
                            "count": count
                        }
                    ))

        # 更新实体历史
        for entity in current_entities:
            self._entity_history[entity].append(entity)
            if len(self._entity_history[entity]) > 100:
                self._entity_history[entity] = self._entity_history[entity][-100:]

        return alerts

    _STOP_WORDS = {
        "我们", "他们", "它们", "你们", "她们", "这个", "那个",
        "什么", "如何", "为什么", "因为", "所以", "但是", "而且",
        "不是", "就是", "可以", "没有", "如果", "一个", "进行",
        "以及", "或者", "关于", "根据", "通过", "同时", "还是",
        "已经", "成为", "表示", "提供", "发布", "包括", "相关",
        "主要", "目前", "今天", "昨天", "明天", "去年", "今年"
    }

    def _detect_topic_anomalies(self, news_items: List[Dict]) -> List[AnomalyAlert]:
        """检测话题异动"""
        alerts = []

        # 按关键词聚类
        topic_keywords = Counter()
        for item in news_items:
            title = item.get('title', '') or ''
            content = item.get('content', '') or item.get('description', '') or ''
            text = f"{title} {content}"

            import re
            # 提取主题词：2-3字中文词
            words = re.findall(r'[\u4e00-\u9fff]{2,3}', text)
            for w in words:
                if w not in self._STOP_WORDS:
                    topic_keywords[w] += 1

        # 检测快速崛起的话题
        for keyword, count in topic_keywords.most_common(20):
            if count >= self.THRESHOLDS["topic"]["min_news_count"]:
                # 检查历史
                history = self._topic_history.get(keyword, [])
                if history:
                    avg = sum(history) / len(history)
                    if avg > 0 and count / avg > 3:
                        alerts.append(AnomalyAlert(
                            type="topic",
                            level="warning",
                            title=f"话题快速升温: {keyword}",
                            description=f"关键词「{keyword}」出现 {count} 次，"
                                        f"相比历史均值 {avg:.1f} 次增长明显",
                            metrics={
                                "keyword": keyword,
                                "current_count": count,
                                "historical_avg": avg,
                                "ratio": count / avg if avg > 0 else 0
                            }
                        ))

                # 更新话题历史
                self._topic_history[keyword].append(count)
                if len(self._topic_history[keyword]) > 20:
                    self._topic_history[keyword] = self._topic_history[keyword][-20:]

        return alerts

    def _detect_cross_platform_resonance(self, news_items: List[Dict]) -> List[AnomalyAlert]:
        """检测跨平台共振"""
        alerts = []

        # 按标题关键词聚类
        title_groups = defaultdict(list)
        for item in news_items:
            title = item.get('title', '') or ''
            source = item.get('source', '') or ''
            # 使用前10个字作为聚类键
            key = title[:10] if len(title) >= 5 else title
            title_groups[key].append(item)

        # 检测多平台同时关注的话题
        for key, items in title_groups.items():
            if len(items) >= self.THRESHOLDS["cross_platform"]["min_news_count"]:
                platforms = set()
                for item in items:
                    src = item.get('source', '')
                    if src and not any(p in src for p in ['搜狐', '头条', '百家号']):
                        platforms.add(src)

                if len(platforms) >= self.THRESHOLDS["cross_platform"]["min_platforms"]:
                    alerts.append(AnomalyAlert(
                        type="cross_platform",
                        level="info",
                        title="跨平台共振话题",
                        description=f"话题在 {len(platforms)} 个平台同时出现 "
                                    f"({', '.join(list(platforms)[:5])})，"
                                    f"共 {len(items)} 条相关新闻",
                        related_items=items[:5],
                        metrics={
                            "platforms": list(platforms),
                            "platform_count": len(platforms),
                            "news_count": len(items),
                            "topic_key": key
                        }
                    ))

        return alerts

    def get_alerts(self, limit: int = 50, level: Optional[str] = None,
                   alert_type: Optional[str] = None) -> List[Dict]:
        """获取告警记录"""
        results = list(self._alerts)

        if level:
            results = [a for a in results if a.level == level]
        if alert_type:
            results = [a for a in results if a.type == alert_type]

        # 按时间倒序
        results.reverse()
        return [asdict(a) for a in results[:limit]]

    def get_alert_statistics(self) -> Dict:
        """获取告警统计"""
        stats = {
            "total": len(self._alerts),
            "by_level": Counter(a.level for a in self._alerts),
            "by_type": Counter(a.type for a in self._alerts),
            "recent_24h": 0,
            "thresholds": self.THRESHOLDS
        }

        # 24小时内告警数
        now = datetime.now()
        for alert in self._alerts:
            try:
                alert_time = datetime.strptime(alert.timestamp, "%Y-%m-%d %H:%M:%S")
                if (now - alert_time).total_seconds() < 86400:
                    stats["recent_24h"] += 1
            except ValueError:
                pass

        return {
            "total": stats["total"],
            "by_level": dict(stats["by_level"]),
            "by_type": dict(stats["by_type"]),
            "recent_24h": stats["recent_24h"],
            "thresholds": stats["thresholds"]
        }


# 全局实例
_monitor_instance = None


def get_opinion_monitor():
    """获取舆情监控器实例（单例模式）"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = OpinionMonitor()
    return _monitor_instance


if __name__ == "__main__":
    # 测试代码
    monitor = get_opinion_monitor()

    test_news = [
        {"title": "突发！全球AI监管框架达成重要共识",
         "source": "新华社", "hot_score": 950,
         "content": "多国代表在日内瓦就人工智能监管达成重要共识..."},
        {"title": "AI监管新规引发业界热议",
         "source": "澎湃新闻", "hot_score": 880,
         "content": "新出台的AI监管规定在科技界引发广泛讨论..."},
        {"title": "专家分析AI监管对行业的影响",
         "source": "财新网", "hot_score": 720,
         "content": "多位专家学者对AI监管政策进行深入分析..."},
    ]

    print("=" * 60)
    print("舆情异常检测系统测试")
    print("=" * 60)

    # 模拟情感数据
    sentiment = {
        "positive_ratio": 0.35,
        "negative_ratio": 0.18,
        "neutral_ratio": 0.47
    }

    alerts = monitor.analyze(test_news, sentiment, force=True)

    print(f"\n检测到 {len(alerts)} 个异常:" if alerts else "\n✅ 未检测到异常")
    for alert in alerts:
        level_icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(alert.level, "📢")
        print(f"\n{level_icon} [{alert.type}] {alert.title}")
        print(f"  描述: {alert.description}")
        print(f"  级别: {alert.level}")

    print(f"\n告警统计:")
    stats = monitor.get_alert_statistics()
    for k, v in stats.items():
        if k != "thresholds":
            print(f"  {k}: {v}")
