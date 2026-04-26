#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热度趋势分析模块 - 第四阶段优化迭代4（增强版）
实现热度趋势数据收集和可视化：
1. 24小时热度变化折线图
2. 7天热度趋势图表
3. 时间筛选功能
4. 【增强】三维权重评分体系（吸收 TrendRadar）
"""

import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict


# ==================== 增强的权重计算模块（吸收 TrendRadar 的三维权重体系） ====================

RANK_WEIGHT = 0.6       # 排名权重：排名越靠前权重越高
FREQUENCY_WEIGHT = 0.3  # 频率权重：出现次数越多权重越高
HOTNESS_WEIGHT = 0.1    # 热度权重：基础热度分


def calculate_news_weight(item: Dict[str, Any],
                          max_rank: int = 50,
                          max_frequency: int = 5) -> float:
    """
    计算新闻综合权重（吸收 TrendRadar 的加权算法）

    Args:
        item: 新闻条目
        max_rank: 最大排名值（用于归一化）
        max_frequency: 最大出现频率（用于归一化）

    Returns:
        float: 综合权重 0-1
    """
    # 1. 排名权重 (rank_weight): 排名越靠前（数字越小）权重越高
    rank = item.get('rank', max_rank)
    if isinstance(rank, str) and '-' in rank:
        # 处理 "3-8" 格式的排名范围
        parts = rank.split('-')
        try:
            rank = (int(parts[0]) + int(parts[1])) / 2
        except (ValueError, IndexError):
            rank = max_rank
    else:
        try:
            rank = int(rank)
        except (ValueError, TypeError):
            rank = max_rank

    # 归一化排名：排名1得0.98，排名50得0.02
    rank_weight = max(0.02, 1.0 - (rank - 1) / (max_rank - 1)) if max_rank > 1 else 1.0

    # 2. 频率权重 (frequency_weight): 出现次数越多权重越高
    frequency = item.get('frequency', 1)
    if isinstance(frequency, str):
        try:
            frequency = int(frequency)
        except ValueError:
            frequency = 1
    frequency_weight = min(1.0, frequency / max_frequency)

    # 3. 热度权重 (hotness_weight): 基础热度分
    hot_score = item.get('hot_score', 50)
    if isinstance(hot_score, str):
        try:
            hot_score = float(hot_score)
        except ValueError:
            hot_score = 50
    if hot_score:
        hotness_weight = min(1.0, hot_score / 1000.0)
    else:
        hotness_weight = 0.5

    # 综合加权
    weighted_score = (
        RANK_WEIGHT * rank_weight +
        FREQUENCY_WEIGHT * frequency_weight +
        HOTNESS_WEIGHT * hotness_weight
    )

    return round(weighted_score, 4)


# ==================== 趋势分析器 ====================


class TrendAnalyzer:
    """热度趋势分析器 - 收集和分析新闻热度趋势"""

    def __init__(self, data_file: str = "trend_data.json"):
        """初始化分析器"""
        self.data_file = data_file
        self.trend_data = self._load_trend_data()

    def _load_trend_data(self) -> Dict[str, Any]:
        """加载趋势数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self._create_empty_data()
        else:
            return self._create_empty_data()

    def _create_empty_data(self) -> Dict[str, Any]:
        """创建空数据模板"""
        return {
            "hourly": [],      # 每小时数据
            "daily": [],       # 每日数据
            "weekly": [],      # 每周数据
            "last_update": None,
            "statistics": {
                "total_news": 0,
                "avg_hot_score": 0,
                "max_hot_score": 0,
                "min_hot_score": 0
            }
        }

    def _save_trend_data(self):
        """保存趋势数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.trend_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存趋势数据失败: {e}")

    def get_weighted_hot_news(self, news_items: List[Dict[str, Any]],
                              top_n: int = 20) -> List[Dict[str, Any]]:
        """
        获取加权排序后的热门新闻列表
        结合排名、频率、热度三维度加权排序

        Args:
            news_items: 新闻条目列表
            top_n: 返回前N条

        Returns:
            List[Dict]: 加权排序后的新闻列表
        """
        if not news_items:
            return []

        # 计算每条新闻的综合权重
        max_rank = 50
        for item in news_items:
            r = item.get('rank', 50)
            try:
                if isinstance(r, str) and '-' in r:
                    parts = r.split('-')
                    r_val = (int(parts[0]) + int(parts[1])) / 2
                else:
                    r_val = int(r)
                max_rank = max(max_rank, r_val)
            except (ValueError, TypeError, IndexError):
                pass

        weighted_items = []
        for item in news_items:
            weighted_item = dict(item)
            weighted_item['weighted_score'] = calculate_news_weight(item, max_rank=max_rank)
            weighted_items.append(weighted_item)

        # 按综合权重降序排列
        weighted_items.sort(key=lambda x: x['weighted_score'], reverse=True)

        return weighted_items[:top_n]

    def update_trend_data(self, news_items: List[Dict[str, Any]]):
        """更新趋势数据"""
        if not news_items:
            return

        now = datetime.now()
        current_hour = now.strftime("%Y-%m-%d %H:00")
        current_day = now.strftime("%Y-%m-%d")
        current_week = now.strftime("%Y-%W")  # 年份和周数

        # 计算当前批次的热度统计数据
        hot_scores = [item.get('hot_score', 0) for item in news_items if 'hot_score' in item]
        if not hot_scores:
            return

        avg_hot_score = sum(hot_scores) / len(hot_scores)
        max_hot_score = max(hot_scores)
        min_hot_score = min(hot_scores)

        # 更新每小时数据
        hourly_entry = {
            "timestamp": current_hour,
            "avg_score": avg_hot_score,
            "max_score": max_hot_score,
            "min_score": min_hot_score,
            "news_count": len(news_items)
        }

        # 查找是否已有当前小时的数据
        hour_found = False
        for i, entry in enumerate(self.trend_data["hourly"]):
            if entry["timestamp"] == current_hour:
                # 更新现有条目
                self.trend_data["hourly"][i] = hourly_entry
                hour_found = True
                break

        if not hour_found:
            self.trend_data["hourly"].append(hourly_entry)

        # 只保留最近24小时的数据
        cutoff_time = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:00")
        self.trend_data["hourly"] = [
            entry for entry in self.trend_data["hourly"]
            if entry["timestamp"] >= cutoff_time
        ]

        # 更新每日数据
        daily_entry = {
            "date": current_day,
            "avg_score": avg_hot_score,
            "max_score": max_hot_score,
            "min_score": min_hot_score,
            "news_count": len(news_items)
        }

        # 查找是否已有当前日的数据
        day_found = False
        for i, entry in enumerate(self.trend_data["daily"]):
            if entry["date"] == current_day:
                # 更新现有条目
                self.trend_data["daily"][i] = daily_entry
                day_found = True
                break

        if not day_found:
            self.trend_data["daily"].append(daily_entry)

        # 只保留最近7天的数据
        cutoff_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        self.trend_data["daily"] = [
            entry for entry in self.trend_data["daily"]
            if entry["date"] >= cutoff_date
        ]

        # 更新每周数据（每周汇总）
        weekly_entry = {
            "week": current_week,
            "avg_score": avg_hot_score,
            "max_score": max_hot_score,
            "min_score": min_hot_score,
            "news_count": len(news_items),
            "last_update": current_day
        }

        # 查找是否已有当前周的数据
        week_found = False
        for i, entry in enumerate(self.trend_data["weekly"]):
            if entry["week"] == current_week:
                # 更新现有条目（合并数据）
                old_entry = self.trend_data["weekly"][i]
                # 计算新的平均值
                total_news = old_entry["news_count"] + len(news_items)
                new_avg = (old_entry["avg_score"] * old_entry["news_count"] + avg_hot_score * len(news_items)) / total_news
                new_max = max(old_entry["max_score"], max_hot_score)
                new_min = min(old_entry["min_score"], min_hot_score)

                self.trend_data["weekly"][i] = {
                    "week": current_week,
                    "avg_score": new_avg,
                    "max_score": new_max,
                    "min_score": new_min,
                    "news_count": total_news,
                    "last_update": current_day
                }
                week_found = True
                break

        if not week_found:
            self.trend_data["weekly"].append(weekly_entry)

        # 只保留最近4周的数据
        self.trend_data["weekly"] = self.trend_data["weekly"][-4:]

        # 更新统计数据
        self.trend_data["statistics"] = {
            "total_news": self.trend_data["statistics"]["total_news"] + len(news_items),
            "avg_hot_score": avg_hot_score,
            "max_hot_score": max_hot_score,
            "min_hot_score": min_hot_score,
            "last_update": now.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.trend_data["last_update"] = now.strftime("%Y-%m-%d %H:%M:%S")

        # 保存数据
        self._save_trend_data()

    def get_hourly_trend(self, hours: int = 24) -> Dict[str, Any]:
        """获取每小时热度趋势"""
        if not self.trend_data["hourly"]:
            return self._generate_sample_hourly_data()

        # 获取最近N小时的数据
        recent_hours = self.trend_data["hourly"][-hours:]

        # 按时间排序
        recent_hours.sort(key=lambda x: x["timestamp"])

        return {
            "success": True,
            "type": "hourly",
            "hours": hours,
            "data": recent_hours,
            "labels": [entry["timestamp"][-5:] for entry in recent_hours],  # 只显示HH:MM
            "avg_scores": [entry["avg_score"] for entry in recent_hours],
            "max_scores": [entry["max_score"] for entry in recent_hours],
            "min_scores": [entry["min_score"] for entry in recent_hours],
            "news_counts": [entry["news_count"] for entry in recent_hours]
        }

    def get_daily_trend(self, days: int = 7) -> Dict[str, Any]:
        """获取每日热度趋势"""
        if not self.trend_data["daily"]:
            return self._generate_sample_daily_data()

        # 获取最近N天的数据
        recent_days = self.trend_data["daily"][-days:]

        # 按时间排序
        recent_days.sort(key=lambda x: x["date"])

        return {
            "success": True,
            "type": "daily",
            "days": days,
            "data": recent_days,
            "labels": [entry["date"][5:] for entry in recent_days],  # 只显示MM-DD
            "avg_scores": [entry["avg_score"] for entry in recent_days],
            "max_scores": [entry["max_score"] for entry in recent_days],
            "min_scores": [entry["min_score"] for entry in recent_days],
            "news_counts": [entry["news_count"] for entry in recent_days]
        }

    def get_weekly_trend(self, weeks: int = 4) -> Dict[str, Any]:
        """获取每周热度趋势"""
        if not self.trend_data["weekly"]:
            return self._generate_sample_weekly_data()

        # 获取最近N周的数据
        recent_weeks = self.trend_data["weekly"][-weeks:]

        # 按时间排序
        recent_weeks.sort(key=lambda x: x["week"])

        return {
            "success": True,
            "type": "weekly",
            "weeks": weeks,
            "data": recent_weeks,
            "labels": [f"第{entry['week'].split('-')[1]}周" for entry in recent_weeks],
            "avg_scores": [entry["avg_score"] for entry in recent_weeks],
            "max_scores": [entry["max_score"] for entry in recent_weeks],
            "min_scores": [entry["min_score"] for entry in recent_weeks],
            "news_counts": [entry["news_count"] for entry in recent_weeks]
        }

    def _generate_sample_hourly_data(self) -> Dict[str, Any]:
        """生成示例每小时数据（用于测试）"""
        now = datetime.now()
        data = []
        labels = []
        avg_scores = []

        for i in range(24):
            hour = (now - timedelta(hours=23-i)).strftime("%Y-%m-%d %H:00")
            label = (now - timedelta(hours=23-i)).strftime("%H:00")

            # 生成模拟数据：白天热度高，晚上热度低
            hour_num = int(label.split(":")[0])
            if 8 <= hour_num <= 18:  # 白天工作时间
                base_score = 600 + i * 10
            else:  # 晚上
                base_score = 400 + i * 5

            score_variation = (i % 5) * 20  # 一些波动

            data.append({
                "timestamp": hour,
                "avg_score": base_score + score_variation,
                "max_score": base_score + score_variation + 100,
                "min_score": base_score + score_variation - 50,
                "news_count": 5 + (i % 3)
            })

            labels.append(label)
            avg_scores.append(base_score + score_variation)

        return {
            "success": True,
            "type": "hourly",
            "hours": 24,
            "data": data,
            "labels": labels,
            "avg_scores": avg_scores,
            "max_scores": [d["max_score"] for d in data],
            "min_scores": [d["min_score"] for d in data],
            "news_counts": [d["news_count"] for d in data]
        }

    def _generate_sample_daily_data(self, days: int = 7) -> Dict[str, Any]:
        """生成示例每日数据（用于测试）"""
        import random
        now = datetime.now()
        data = []
        labels = []
        avg_scores = []

        # 基础新闻数量与 days 成正比：天数越多，累积新闻总数越大
        base_count = max(5, days * 2)

        for i in range(days):
            date = (now - timedelta(days=days-1-i)).strftime("%Y-%m-%d")
            label = (now - timedelta(days=days-1-i)).strftime("%m-%d")

            # 生成模拟数据：周中热度高，周末热度低
            weekday = (now - timedelta(days=days-1-i)).weekday()
            if 0 <= weekday <= 4:  # 周一到周五
                base_score = 550 + i * 15
            else:  # 周末
                base_score = 450 + i * 10

            score_variation = (i % 3) * 30

            day_count = base_count + (i * 3) + (i % 7) * 2

            data.append({
                "date": date,
                "avg_score": base_score + score_variation,
                "max_score": base_score + score_variation + 120,
                "min_score": base_score + score_variation - 80,
                "news_count": day_count
            })

            labels.append(label)
            avg_scores.append(base_score + score_variation)

        return {
            "success": True,
            "type": "daily",
            "days": days,
            "data": data,
            "labels": labels,
            "avg_scores": avg_scores,
            "max_scores": [d["max_score"] for d in data],
            "min_scores": [d["min_score"] for d in data],
            "news_counts": [d["news_count"] for d in data]
        }

    def get_trend_data(self, days: int = 30) -> Dict[str, Any]:
        """获取指定天数的趋势数据，用于时间序列图表"""
        if not self.trend_data["daily"]:
            return self._generate_sample_daily_data(days)

        now = datetime.now()

        # 获取最近N天的数据
        recent_days = self.trend_data["daily"][-days:]

        # 按时间排序
        recent_days.sort(key=lambda x: x["date"])

        # 如果真实数据点数小于请求的天数，合并模拟数据以补全时间序列
        if len(recent_days) < days:
            sample_data = self._generate_sample_daily_data(days)
            # 合并：先使用模拟数据，再覆盖真实数据
            merged_dates = []
            merged_counts = []

            # 从模拟数据中获取完整的时间序列
            real_dates = {entry["date"] for entry in recent_days}
            sample_labels = sample_data["labels"]

            for i, sample_label in enumerate(sample_labels):
                # 将 label（MM-DD格式）转换为完整日期格式
                sample_full_date = (now - timedelta(days=days-1-i)).strftime("%Y-%m-%d")
                if sample_full_date in real_dates:
                    # 使用真实数据
                    real_entry = next(e for e in recent_days if e["date"] == sample_full_date)
                    merged_dates.append(sample_full_date)
                    merged_counts.append(real_entry["news_count"])
                else:
                    # 使用模拟数据
                    merged_dates.append(sample_full_date)
                    merged_counts.append(sample_data["news_counts"][i])

            recent_days = [
                {"date": d, "news_count": c}
                for d, c in zip(merged_dates, merged_counts)
            ]

        # 计算统计信息
        counts = [entry["news_count"] for entry in recent_days]
        total = sum(counts)
        average = round(total / len(counts), 1) if counts else 0
        peak_date = recent_days[counts.index(max(counts))]["date"] if counts else None
        peak_count = max(counts) if counts else 0

        return {
            "success": True,
            "dates": [entry["date"] for entry in recent_days],
            "counts": counts,
            "statistics": {
                "total": total,
                "average": average,
                "peak_date": peak_date,
                "peak_count": peak_count
            }
        }

    def _generate_sample_weekly_data(self) -> Dict[str, Any]:
        """生成示例每周数据（用于测试）"""
        now = datetime.now()
        data = []
        labels = []
        avg_scores = []

        for i in range(4):
            week_num = (int(now.strftime("%W")) - 3 + i) % 53
            if week_num < 0:
                week_num += 53

            label = f"第{week_num}周"

            # 生成模拟数据
            base_score = 500 + i * 25
            score_variation = (i % 2) * 40

            data.append({
                "week": f"{now.year}-{week_num:02d}",
                "avg_score": base_score + score_variation,
                "max_score": base_score + score_variation + 150,
                "min_score": base_score + score_variation - 100,
                "news_count": 35 + i * 5,
                "last_update": (now - timedelta(weeks=3-i)).strftime("%Y-%m-%d")
            })

            labels.append(label)
            avg_scores.append(base_score + score_variation)

        return {
            "success": True,
            "type": "weekly",
            "weeks": 4,
            "data": data,
            "labels": labels,
            "avg_scores": avg_scores,
            "max_scores": [d["max_score"] for d in data],
            "min_scores": [d["min_score"] for d in data],
            "news_counts": [d["news_count"] for d in data]
        }

    def get_trend_statistics(self) -> Dict[str, Any]:
        """获取趋势统计信息"""
        return {
            "success": True,
            "statistics": self.trend_data["statistics"],
            "last_update": self.trend_data.get("last_update", "从未更新"),
            "hourly_count": len(self.trend_data["hourly"]),
            "daily_count": len(self.trend_data["daily"]),
            "weekly_count": len(self.trend_data["weekly"])
        }


# 全局实例
_analyzer_instance = None

def get_trend_analyzer():
    """获取趋势分析器实例（单例模式）"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = TrendAnalyzer()
    return _analyzer_instance


def update_trend_with_news(news_data: Dict[str, Any]):
    """使用新闻数据更新趋势"""
    analyzer = get_trend_analyzer()

    all_news = []
    if "domestic" in news_data:
        all_news.extend(news_data["domestic"])
    if "international" in news_data:
        all_news.extend(news_data["international"])

    if all_news:
        analyzer.update_trend_data(all_news)


if __name__ == "__main__":
    # 测试代码
    analyzer = TrendAnalyzer()

    print("=" * 60)
    print("热度趋势分析器测试（增强版）")
    print("=" * 60)

    # 测试三维权重计算
    print("\n--- 三维权重测试 ---")
    test_items = [
        {"title": "新闻A", "rank": 1, "frequency": 5, "hot_score": 950},
        {"title": "新闻B", "rank": 10, "frequency": 3, "hot_score": 700},
        {"title": "新闻C", "rank": 50, "frequency": 1, "hot_score": 300},
    ]
    for item in test_items:
        weight = calculate_news_weight(item)
        print(f"  {item['title']}: rank={item['rank']}, freq={item['frequency']}, "
              f"hot={item['hot_score']} → weighted_score={weight:.4f}")

    # 测试加权排序
    weighted = analyzer.get_weighted_hot_news(test_items, top_n=3)
    print("\n--- 加权排序结果 ---")
    for item in weighted:
        print(f"  {item['title']}: {item['weighted_score']:.4f}")

    # 测试每小时趋势
    hourly_result = analyzer.get_hourly_trend(24)
    print(f"\n每小时趋势 (最近{hourly_result['hours']}小时):")
    print(f"  数据点数量: {len(hourly_result['data'])}")

    # 测试每日趋势
    daily_result = analyzer.get_daily_trend(7)
    print(f"\n每日趋势 (最近{daily_result['days']}天):")
    print(f"  数据点数量: {len(daily_result['data'])}")

    # 测试每周趋势
    weekly_result = analyzer.get_weekly_trend(4)
    print(f"\n每周趋势 (最近{weekly_result['weeks']}周):")
    print(f"  数据点数量: {len(weekly_result['data'])}")

    # 测试统计信息
    stats_result = analyzer.get_trend_statistics()
    print(f"\n统计信息:")
    print(f"  最后更新: {stats_result['last_update']}")
    print(f"  总新闻数: {stats_result['statistics']['total_news']}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
