#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能兴趣过滤 - 智能新闻工作台
吸收 BestBlogs 的 Agent Skills 和个性化推荐理念：
1. 基于关键词的兴趣配置
2. 多维度内容匹配（标题、内容、来源、实体）
3. 自动学习和更新兴趣权重
4. 定时热点追踪
"""

import os
import json
import re
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict

# 默认兴趣配置文件路径
DEFAULT_INTERESTS_CONFIG = "config/news_interests.json"

# 默认兴趣配置
DEFAULT_INTERESTS = {
    "interests": [
        {
            "name": "人工智能与科技",
            "keywords": ["人工智能", "AI", "机器学习", "大模型", "ChatGPT", "GPT", "深度学习",
                         "智能", "算法", "数据", "芯片", "半导体", "量子计算", "自动驾驶",
                         "机器人", "AI监管", "人工智能治理"],
            "weight": 1.0,
            "categories": ["科技", "tech"],
            "sources": [],
            "enabled": True,
            "min_score": 0
        },
        {
            "name": "经济与金融市场",
            "keywords": ["经济", "金融", "股市", "基金", "投资", "GDP", "通胀", "利率",
                         "人民币", "美元", "贸易", "关税", "制裁", "IPO", "上市",
                         "财报", "营收", "利润", "增长", "企业"],
            "weight": 0.9,
            "categories": ["经济", "财经", "finance"],
            "sources": ["华尔街见闻", "Bloomberg", "Reuters", "路透社", "华尔街日报"],
            "enabled": True,
            "min_score": 0
        },
        {
            "name": "国际政治与地缘",
            "keywords": ["外交", "国际", "制裁", "地缘", "冲突", "战争", "和平",
                         "联合国", "拜登", "特朗普", "普京", "习近平", "中美",
                         "俄乌", "中东", "欧盟", "北约", "东盟", "一带一路",
                         "南海", "台海", "朝鲜", "伊朗"],
            "weight": 0.8,
            "categories": ["国际", "政治", "world"],
            "sources": ["BBC", "CNN", "Reuters", "AP", "路透社"],
            "enabled": True,
            "min_score": 0
        },
        {
            "name": "社会与民生",
            "keywords": ["民生", "房价", "教育", "医疗", "养老", "就业", "社保",
                         "工资", "消费", "物价", "交通", "环保", "疫情",
                         "食品安全", "乡村振兴", "共同富裕"],
            "weight": 0.7,
            "categories": ["社会", "民生", "domestic"],
            "sources": [],
            "enabled": True,
            "min_score": 0
        },
        {
            "name": "能源与环境",
            "keywords": ["新能源", "光伏", "风电", "锂电池", "电动汽车", "碳中和",
                         "碳排放", "气候变化", "环保", "绿色", "能源", "石油", "天然气",
                         "核能", "氢能"],
            "weight": 0.6,
            "categories": ["能源", "环境", "green"],
            "sources": [],
            "enabled": True,
            "min_score": 0
        }
    ],
    "global_settings": {
        "auto_learn": True,
        "boost_by_trend": True,
        "min_match_score": 0.1,
        "max_news_per_interest": 20
    }
}


@dataclass
class InterestMatchResult:
    """兴趣匹配结果"""
    interest_name: str
    match_score: float
    matched_keywords: List[str]
    categories: List[str]
    weight: float
    final_score: float


@dataclass
class FilteredNewsItem:
    """过滤后的新闻条目，带匹配信息"""
    news_item: Dict[str, Any]
    matches: List[InterestMatchResult]
    best_interest: str
    best_score: float


class InterestConfig:
    """兴趣配置文件管理器"""

    def __init__(self, config_path: str = DEFAULT_INTERESTS_CONFIG):
        self.config_path = config_path
        self._config = self._load_config()
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        config_dir = os.path.dirname(self.config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)

    def _load_config(self) -> Dict:
        """加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载兴趣配置失败: {e}")

        # 创建默认配置
        self._save_config(DEFAULT_INTERESTS)
        return dict(DEFAULT_INTERESTS)

    def _save_config(self, config: Dict):
        """保存配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存兴趣配置失败: {e}")

    def get_interests(self) -> List[Dict]:
        """获取兴趣列表"""
        return self._config.get("interests", [])

    def get_settings(self) -> Dict:
        """获取全局设置"""
        return self._config.get("global_settings", {})

    def add_interest(self, interest: Dict) -> bool:
        """添加兴趣"""
        interests = self._config.setdefault("interests", [])
        # 检查是否已存在
        for i, existing in enumerate(interests):
            if existing.get("name") == interest.get("name"):
                interests[i] = interest
                self._save_config(self._config)
                return True
        interests.append(interest)
        self._save_config(self._config)
        return True

    def remove_interest(self, name: str) -> bool:
        """删除兴趣"""
        interests = self._config.get("interests", [])
        self._config["interests"] = [i for i in interests if i.get("name") != name]
        self._save_config(self._config)
        return True

    def update_settings(self, settings: Dict) -> bool:
        """更新全局设置"""
        self._config["global_settings"] = {
            **self._config.get("global_settings", {}),
            **settings
        }
        self._save_config(self._config)
        return True

    def save(self):
        """保存当前配置"""
        self._save_config(self._config)


class AIFilter:
    """AI智能兴趣过滤器"""

    def __init__(self, config_path: str = DEFAULT_INTERESTS_CONFIG):
        self.config = InterestConfig(config_path)
        self._keyword_cache = {}  # 缓存编译后的关键词

    def _get_compiled_keywords(self, keywords: List[str]) -> List[re.Pattern]:
        """获取编译后的关键词正则"""
        cache_key = ",".join(sorted(keywords))
        if cache_key in self._keyword_cache:
            return self._keyword_cache[cache_key]

        patterns = []
        for kw in keywords:
            try:
                # 对关键词进行正则转义，但保留中文和英文匹配
                patterns.append(re.compile(re.escape(kw), re.IGNORECASE))
            except re.error:
                continue

        self._keyword_cache[cache_key] = patterns
        return patterns

    def _calculate_match_score(self, news_item: Dict[str, Any],
                               interest: Dict) -> Tuple[float, List[str]]:
        """
        计算新闻与兴趣的匹配度

        Args:
            news_item: 新闻条目
            interest: 兴趣配置

        Returns:
            Tuple[float, List[str]]: (匹配分数, 匹配到的关键词)
        """
        # 构建匹配文本
        title = news_item.get('title', '') or ''
        content = news_item.get('content', '') or news_item.get('description', '') or ''
        source = news_item.get('source', '') or ''
        category = news_item.get('category', news_item.get('region', '')) or ''

        text = f"{title} {content} {source} {category}"

        # 关键词匹配
        keywords = interest.get("keywords", [])
        patterns = self._get_compiled_keywords(keywords)

        matched_keywords = []
        for kw, pattern in zip(keywords, patterns):
            if pattern.search(text):
                matched_keywords.append(kw)

        if not matched_keywords:
            return 0.0, []

        # 匹配权重：标题匹配权重更高
        title_matches = sum(1 for kw in matched_keywords if kw.lower() in title.lower())
        content_matches = len(matched_keywords) - title_matches
        total_keywords = len(keywords)

        if total_keywords == 0:
            return 0.0, []

        # 基础匹配率
        base_rate = len(matched_keywords) / total_keywords

        # 标题加权
        title_bonus = (title_matches / max(len(matched_keywords), 1)) * 0.3

        # 来源匹配加分
        interest_sources = [s.lower() for s in interest.get("sources", [])]
        source_bonus = 0.15 if source.lower() in interest_sources else 0

        # 分类匹配加分
        interest_categories = [c.lower() for c in interest.get("categories", [])]
        category_bonus = 0.1 if category.lower() in interest_categories else 0

        score = min(1.0, base_rate + title_bonus + source_bonus + category_bonus)

        return score, matched_keywords

    def filter_news(self, news_items: List[Dict[str, Any]],
                    interest_name: Optional[str] = None) -> List[FilteredNewsItem]:
        """
        过滤新闻，返回匹配结果

        Args:
            news_items: 新闻条目列表
            interest_name: 指定兴趣名称，None表示匹配所有兴趣

        Returns:
            List[FilteredNewsItem]: 过滤后的新闻列表
        """
        interests = self.config.get_interests()
        settings = self.config.get_settings()

        if interest_name:
            interests = [i for i in interests if i.get("name") == interest_name]

        if not interests:
            return []

        min_score = settings.get("min_match_score", 0.1)
        results = []

        for item in news_items:
            matches = []

            for interest in interests:
                if not interest.get("enabled", True):
                    continue

                score, matched_keywords = self._calculate_match_score(item, interest)

                if score >= min_score and len(matched_keywords) >= interest.get("min_score", 0):
                    weight = interest.get("weight", 1.0)
                    final_score = score * weight

                    matches.append(InterestMatchResult(
                        interest_name=interest.get("name", "未知"),
                        match_score=round(score, 3),
                        matched_keywords=matched_keywords[:10],
                        categories=interest.get("categories", []),
                        weight=weight,
                        final_score=round(final_score, 3)
                    ))

            if matches:
                # 按最终分数排序
                matches.sort(key=lambda m: m.final_score, reverse=True)
                results.append(FilteredNewsItem(
                    news_item=item,
                    matches=matches,
                    best_interest=matches[0].interest_name,
                    best_score=matches[0].final_score
                ))

        # 按最佳匹配分数降序
        results.sort(key=lambda r: r.best_score, reverse=True)

        # 应用每类兴趣的数量限制
        max_per_interest = settings.get("max_news_per_interest", 20)
        limited_results = []
        interest_counts = {}

        for result in results:
            name = result.best_interest
            interest_counts[name] = interest_counts.get(name, 0) + 1
            if interest_counts[name] <= max_per_interest:
                limited_results.append(result)

        return limited_results

    def get_filtered_by_interest(self, news_items: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """
        按兴趣分组过滤新闻

        Args:
            news_items: 新闻条目列表

        Returns:
            Dict[str, List[Dict]]: 按兴趣名称分组的新闻
        """
        filtered = self.filter_news(news_items)
        grouped = {}

        for result in filtered:
            name = result.best_interest
            if name not in grouped:
                grouped[name] = []
            grouped[name].append({
                "news": result.news_item,
                "match_score": result.best_score,
                "matched_keywords": result.matches[0].matched_keywords if result.matches else [],
                "all_matches": [
                    {
                        "interest": m.interest_name,
                        "score": m.final_score,
                        "keywords": m.matched_keywords
                    }
                    for m in result.matches
                ]
            })

        return grouped

    def get_config(self) -> Dict:
        """获取完整配置"""
        return {
            "interests": self.config.get_interests(),
            "settings": self.config.get_settings()
        }


# 全局实例
_filter_instance = None


def get_ai_filter():
    """获取AI过滤器实例（单例模式）"""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = AIFilter()
    return _filter_instance


if __name__ == "__main__":
    # 测试代码
    filter_engine = get_ai_filter()

    test_news = [
        {"title": "OpenAI发布GPT-5模型，人工智能能力再上新台阶",
         "content": "OpenAI今日正式发布了其最新的大语言模型GPT-5...",
         "source": "澎湃新闻", "category": "科技"},
        {"title": "美联储宣布加息25个基点，全球金融市场震荡",
         "content": "美联储在最新议息会议上决定加息25个基点...",
         "source": "Bloomberg", "category": "财经"},
        {"title": "中美领导人视频会晤讨论双边关系",
         "content": "两国领导人就双边关系和共同关心的国际问题...",
         "source": "新华社", "category": "国际"},
        {"title": "新能源补贴政策调整，光伏行业迎来新机遇",
         "content": "国家能源局发布新能源补贴政策调整方案...",
         "source": "经济日报", "category": "经济"},
    ]

    print("=" * 60)
    print("AI智能兴趣过滤测试")
    print("=" * 60)

    # 测试逐条匹配
    for news in test_news:
        filtered = filter_engine.filter_news([news])
        if filtered:
            r = filtered[0]
            print(f"\n📰 {r.news_item['title'][:40]}...")
            print(f"  最佳匹配: {r.best_interest} (分数: {r.best_score})")
            print(f"  匹配关键词: {', '.join(r.matches[0].matched_keywords[:5])}")
        else:
            print(f"\n📰 {news['title'][:40]}... -> ❌ 无匹配")

    # 测试分组
    print("\n" + "-" * 40)
    grouped = filter_engine.get_filtered_by_interest(test_news)
    for interest_name, items in grouped.items():
        print(f"\n🏷️ {interest_name}: {len(items)}条")
        for item in items:
            print(f"  - {item['news']['title'][:40]} (分数: {item['match_score']})")

    # 显示配置
    print(f"\n兴趣配置数: {len(filter_engine.get_config()['interests'])}")
