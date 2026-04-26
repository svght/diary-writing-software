#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻六维评分系统 - 智能新闻工作台
吸收 BestBlogs 的 AI 评分理念，提供无AI调用的轻量级六维评分：
1. 时效性 (timeliness) - 新闻发布时间的远近
2. 权威性 (authority) - 来源媒体的权威程度
3. 争议性 (controversy) - 话题的争议程度
4. 深度 (depth) - 内容的详细程度
5. 实体丰富度 (entity_richness) - 涉及实体的数量和质量
6. 情感冲击力 (sentiment_impact) - 情感色彩的强烈程度
"""

import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


# 来源权威度评分
SOURCE_AUTHORITY = {
    # 国内权威媒体
    "人民日报": 0.95, "新华社": 0.95, "央视新闻": 0.94, "央视": 0.94,
    "光明日报": 0.92, "经济日报": 0.92, "环球时报": 0.88,
    "中国日报": 0.90, "China Daily": 0.90, "参考消息": 0.89,
    "观察者网": 0.80, "澎湃新闻": 0.82, "新浪新闻": 0.70,
    "腾讯新闻": 0.70, "网易新闻": 0.70, "搜狐新闻": 0.68,
    "新浪财经": 0.72, "华尔街见闻": 0.78, "财新网": 0.85,
    "第一财经": 0.80, "21世纪经济报道": 0.80,
    "凤凰网": 0.75, "凤凰财经": 0.75,
    "中国新闻网": 0.85, "新华网": 0.92, "人民网": 0.92,
    "中国政府网": 0.95, "国防部发布": 0.93,
    "央视军事": 0.90, "军武次位面": 0.65,
    # 国际权威媒体
    "Reuters": 0.95, "路透社": 0.95,
    "AP": 0.93, "美联社": 0.93,
    "AFP": 0.92, "法新社": 0.92,
    "Bloomberg": 0.93, "彭博社": 0.93,
    "BBC": 0.92, "CNN": 0.85,
    "The Guardian": 0.88, "卫报": 0.88,
    "NYT": 0.90, "纽约时报": 0.90,
    "WSJ": 0.90, "华尔街日报": 0.90,
    "The Economist": 0.90, "经济学人": 0.90,
    "FT": 0.88, "金融时报": 0.88,
    "Washington Post": 0.87, "华盛顿邮报": 0.87,
    "Nikkei": 0.82, "日经新闻": 0.82,
    "Kyodo": 0.78, "共同社": 0.78,
    "Yonhap": 0.76, "韩联社": 0.76,
    "TASS": 0.70, "塔斯社": 0.70,
    "Al Jazeera": 0.78, "半岛电视台": 0.78,
    "Russia Today": 0.60, "今日俄罗斯": 0.60,
    "DW": 0.80, "德国之声": 0.80,
}
# 默认权威度
DEFAULT_AUTHORITY = 0.55
UNKNOWN_AUTHORITY = 0.40

# 深度关键词
DEPTH_KEYWORDS = [
    "分析", "解读", "深度", "详解", "揭秘", "调查", "报告",
    "白皮书", "蓝皮书", "研究报告", "年报", "半年报", "季报",
    "专访", "对话", "访谈", "圆桌", "研讨会", "峰会",
    "数据", "统计", "调研", "走访", "实地", "案例",
    "analysis", "report", "deep dive", "investigation",
    "research", "survey", "interview", "in-depth"
]

# 争议性关键词
CONTROVERSY_KEYWORDS = [
    "争议", "质疑", "反对", "抗议", "批评", "谴责", "谴责",
    "辩论", "分歧", "矛盾", "冲突", "争议", "争论",
    "controversy", "dispute", "debate", "criticism",
    "protest", "objection", "disagreement"
]

# 情感冲击力关键词
SENTIMENT_IMPACT_KEYWORDS = {
    "积极": [
        "突破", "创新", "发展", "增长", "提升", "改善",
        "突破性", "里程碑", "历史性", "重大", "重要",
        "胜利", "成功", "成就", "突破", "领先",
        "breakthrough", "milestone", "historic", "achievement"
    ],
    "消极": [
        "危机", "灾难", "事故", "死亡", "损失", "衰退",
        "暴跌", "崩溃", "失败", "丑闻", "腐败",
        "战争", "冲突", "袭击", "恐怖", "制裁",
        "crisis", "disaster", "accident", "death",
        "crash", "collapse", "scandal", "war"
    ]
}

# 六维度的权重
DIMENSION_WEIGHTS = {
    "timeliness": 0.20,
    "authority": 0.15,
    "controversy": 0.15,
    "depth": 0.15,
    "entity_richness": 0.15,
    "sentiment_impact": 0.20
}

DIMENSION_LABELS = {
    "timeliness": "时效性",
    "authority": "权威性",
    "controversy": "争议性",
    "depth": "深度",
    "entity_richness": "实体丰富度",
    "sentiment_impact": "情感冲击力"
}


class NewsScorer:
    """新闻六维评分器"""

    def __init__(self):
        pass

    def get_dimension_scores(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取新闻六维评分

        Args:
            news_item: 新闻条目，包含 title, content, source, hot_score, published 等字段

        Returns:
            Dict: 包含 scores, details, total_score, dimension_labels, dimension_weights
        """
        scores = {}
        details = {}

        # 1. 时效性评分 (0-100)
        timeliness_score, timeliness_detail = self._score_timeliness(news_item)
        scores["timeliness"] = timeliness_score
        details["timeliness"] = timeliness_detail

        # 2. 权威性评分 (0-100)
        authority_score, authority_detail = self._score_authority(news_item)
        scores["authority"] = authority_score
        details["authority"] = authority_detail

        # 3. 争议性评分 (0-100)
        controversy_score, controversy_detail = self._score_controversy(news_item)
        scores["controversy"] = controversy_score
        details["controversy"] = controversy_detail

        # 4. 深度评分 (0-100)
        depth_score, depth_detail = self._score_depth(news_item)
        scores["depth"] = depth_score
        details["depth"] = depth_detail

        # 5. 实体丰富度评分 (0-100)
        entity_score, entity_detail = self._score_entity_richness(news_item)
        scores["entity_richness"] = entity_score
        details["entity_richness"] = entity_detail

        # 6. 情感冲击力评分 (0-100)
        sentiment_score, sentiment_detail = self._score_sentiment_impact(news_item)
        scores["sentiment_impact"] = sentiment_score
        details["sentiment_impact"] = sentiment_detail

        # 计算总分
        total_score = sum(
            scores[dim] * DIMENSION_WEIGHTS[dim]
            for dim in scores
        )
        total_score = round(total_score, 1)

        return {
            "scores": scores,
            "details": details,
            "total_score": total_score,
            "dimension_labels": DIMENSION_LABELS,
            "dimension_weights": DIMENSION_WEIGHTS
        }

    def _score_timeliness(self, item: Dict[str, Any]) -> Tuple[float, str]:
        """时效性评分 - 基于发布时间"""
        # 默认给中等分数
        default_score = 60

        # 尝试从 published 字段获取时间
        published = item.get('published', item.get('pub_date', item.get('date', '')))
        if not published:
            return default_score, "发布时间未知，给予默认60分"

        try:
            # 尝试多种时间格式
            if isinstance(published, str):
                for fmt in [
                    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d",
                    "%Y-%m-%d", "%m-%d %H:%M"
                ]:
                    try:
                        pub_time = datetime.strptime(published, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return default_score, f"无法解析时间格式: {published[:20]}"
            elif isinstance(published, (int, float)):
                pub_time = datetime.fromtimestamp(published)
            else:
                return default_score, "发布时间格式不支持"

            now = datetime.now()
            diff_hours = (now - pub_time).total_seconds() / 3600

            if diff_hours < 1:
                return 98, "1小时内发布，时效性极高"
            elif diff_hours < 3:
                return 95, "3小时内发布，时效性很高"
            elif diff_hours < 6:
                return 90, "6小时内发布，时效性高"
            elif diff_hours < 12:
                return 85, "12小时内发布"
            elif diff_hours < 24:
                return 80, "24小时内发布"
            elif diff_hours < 48:
                return 70, "48小时内发布"
            elif diff_hours < 72:
                return 60, "3天内发布"
            elif diff_hours < 168:
                return 50, "1周内发布"
            else:
                return max(20, int(50 - diff_hours / 168 * 10)), f"{int(diff_hours/24)}天前发布，时效性较低"

        except Exception as e:
            return default_score, f"时间解析异常: {str(e)}"

    def _score_authority(self, item: Dict[str, Any]) -> Tuple[float, str]:
        """权威性评分 - 基于来源媒体"""
        source = (item.get('source', '') or '').strip().lower()

        if not source:
            hot_score = item.get('hot_score', 0)
            if hot_score and hot_score > 500:
                return 65, "来源未知，但热度较高，推测有一定权威性"
            return DEFAULT_AUTHORITY * 100, "来源未知，给予默认评分"

        # 精确匹配
        for media, score in SOURCE_AUTHORITY.items():
            if media.lower() == source:
                return score * 100, f"来源「{media}」权威度评分 {score*100:.0f}"

        # 模糊匹配
        for media, score in sorted(SOURCE_AUTHORITY.items(), key=lambda x: -len(x[0])):
            if media.lower() in source or source in media.lower():
                return score * 100, f"来源「{source}」模糊匹配「{media}」，权威度评分 {score*100:.0f}"

        # 根据关键词判断
        if any(kw in source for kw in ['新闻', 'news', '日报', '晚报', '时报', '周刊', 'channel', 'network']):
            return 60, f"来源「{source}」为新闻类媒体，给予中等权威度评分"
        if any(kw in source for kw in ['blog', 'forum', 'bbs', '自媒体', '头条']):
            return 45, f"来源「{source}」为自媒体/论坛，权威度较低"

        return UNKNOWN_AUTHORITY * 100, f"来源「{source}」未收录权威度数据，给予较低评分"

    def _score_controversy(self, item: Dict[str, Any]) -> Tuple[float, str]:
        """争议性评分 - 基于标题和内容中的争议关键词"""
        title = item.get('title', '') or ''
        content = item.get('content', '') or item.get('description', '') or ''
        text = f"{title} {content}".lower()

        # 统计争议关键词出现次数
        match_count = 0
        matched_keywords = []
        for kw in CONTROVERSY_KEYWORDS:
            if kw.lower() in text:
                match_count += 1
                matched_keywords.append(kw)
                if match_count >= 5:
                    break

        if match_count >= 5:
            score = 85
            detail = f"高度争议性内容，命中{match_count}个争议关键词"
        elif match_count >= 3:
            score = 70
            detail = f"中等争议性内容，命中{match_count}个争议关键词"
        elif match_count >= 1:
            score = 55
            detail = f"略带争议性，命中{match_count}个争议关键词"
        else:
            score = 30
            detail = "无明显争议性内容"

        # 热度修正：热度高的新闻往往争议性也较高
        hot_score = item.get('hot_score', 0)
        if hot_score and hot_score > 700:
            score = min(95, score + 15)
            detail += "，且热度极高可能引发争议"
        elif hot_score and hot_score > 500:
            score = min(90, score + 10)
            detail += "，且热度较高"

        return score, detail

    def _score_depth(self, item: Dict[str, Any]) -> Tuple[float, str]:
        """深度评分 - 基于内容长度和深度关键词"""
        title = item.get('title', '') or ''
        content = item.get('content', '') or item.get('description', '') or ''
        text = f"{title} {content}"

        # 内容长度评分
        content_len = len(text)
        if content_len < 50:
            return 20, "内容过短，缺乏深度"
        elif content_len < 100:
            len_score = 35
            len_detail = "内容较短"
        elif content_len < 200:
            len_score = 50
            len_detail = "内容长度一般"
        elif content_len < 500:
            len_score = 65
            len_detail = "内容长度中等"
        elif content_len < 1000:
            len_score = 78
            len_detail = "内容较丰富"
        else:
            len_score = 88
            len_detail = "内容很丰富"

        # 深度关键词加分
        depth_count = 0
        matched_depth_kw = []
        for kw in DEPTH_KEYWORDS:
            if kw.lower() in text.lower():
                depth_count += 1
                matched_depth_kw.append(kw)
                if depth_count >= 8:
                    break

        depth_bonus = min(20, depth_count * 3)
        if depth_bonus > 0:
            detail = f"{len_detail}，命中{depth_count}个深度关键词，获得{depth_bonus}分加成"
        else:
            detail = len_detail

        return min(100, len_score + depth_bonus), detail

    def _score_entity_richness(self, item: Dict[str, Any]) -> Tuple[float, str]:
        """实体丰富度评分 - 基于标题和内容中的实体数量"""
        title = item.get('title', '') or ''
        content = item.get('content', '') or item.get('description', '') or ''
        text = f"{title} {content}"

        # 使用正则提取可能的人名、地名、组织名
        # 中文实体：2-6字的中文词（人名、地名、机构名）
        chinese_entities = set(re.findall(r'[\u4e00-\u9fff]{2,6}', text))

        # 英文实体：大写开头的单词组合
        eng_entities = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text))

        all_entities = chinese_entities | eng_entities

        # 过滤掉过长的词
        all_entities = {e for e in all_entities if len(e) >= 2 and len(e) <= 20}

        # 排除非实体词
        stop_words = {
            "我们", "他们", "它们", "你们", "她们", "大家", "这个", "那个",
            "什么", "如何", "为什么", "因为", "所以", "但是", "而且",
            "不是", "就是", "可以", "没有", "如果", "一个", "进行",
            "以及", "或者", "关于", "根据", "通过", "同时", "还是",
            "The", "This", "That", "These", "Those", "What", "How", "Why"
        }
        all_entities -= stop_words

        entity_count = len(all_entities)

        if entity_count >= 20:
            score = 90
            detail = f"实体丰富，提取到{entity_count}个潜在实体"
        elif entity_count >= 12:
            score = 75
            detail = f"实体较丰富，提取到{entity_count}个潜在实体"
        elif entity_count >= 6:
            score = 60
            detail = f"实体数量适中，提取到{entity_count}个潜在实体"
        elif entity_count >= 3:
            score = 45
            detail = f"实体较少，仅提取到{entity_count}个潜在实体"
        elif entity_count >= 1:
            score = 30
            detail = f"实体很少，仅提取到{entity_count}个潜在实体"
        else:
            score = 15
            detail = "未提取到实体"

        # 标题中是否有知名实体（加分）
        title_entities = set(re.findall(r'[\u4e00-\u9fff]{2,4}', title))
        if title_entities:
            score = min(100, score + 5)
            detail += "，标题包含实体"

        return score, detail

    def _score_sentiment_impact(self, item: Dict[str, Any]) -> Tuple[float, str]:
        """情感冲击力评分 - 基于情感关键词的强度和密度"""
        title = item.get('title', '') or ''
        content = item.get('content', '') or item.get('description', '') or ''
        text = f"{title} {content}".lower()

        # 统计积极和消极关键词
        positive_count = 0
        negative_count = 0
        matched_positive = []
        matched_negative = []

        for kw in SENTIMENT_IMPACT_KEYWORDS["积极"]:
            if kw.lower() in text:
                positive_count += 1
                matched_positive.append(kw)

        for kw in SENTIMENT_IMPACT_KEYWORDS["消极"]:
            if kw.lower() in text:
                negative_count += 1
                matched_negative.append(kw)

        # 情感冲击力取决于情感词的总体数量和强度
        total_emotion_words = positive_count + negative_count

        if total_emotion_words >= 10:
            score = 85
            detail = f"情感冲击力强，包含{positive_count}个积极词和{negative_count}个消极词"
        elif total_emotion_words >= 6:
            score = 70
            detail = f"情感冲击力中等偏强，包含{positive_count}个积极词和{negative_count}个消极词"
        elif total_emotion_words >= 3:
            score = 55
            detail = f"情感冲击力中等，包含{positive_count}个积极词和{negative_count}个消极词"
        elif total_emotion_words >= 1:
            score = 40
            detail = f"情感冲击力较弱，仅{total_emotion_words}个情感词"
        else:
            score = 25
            detail = "无明显情感色彩"

        # 如果有积极和消极关键词同时出现，说明情感复杂，冲击力更强
        if positive_count > 0 and negative_count > 0:
            score = min(95, score + 10)
            detail += "，存在情感对立增强冲击力"

        return score, detail

    def score_news_batch(self, news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量评分

        Args:
            news_items: 新闻条目列表

        Returns:
            List[Dict]: 包含评分结果的新闻列表
        """
        scored_items = []
        for item in news_items:
            result = self.get_dimension_scores(item)
            scored_item = dict(item)
            scored_item["_scores"] = result["scores"]
            scored_item["_details"] = result["details"]
            scored_item["_total_score"] = result["total_score"]
            scored_item["_dimension_labels"] = result["dimension_labels"]
            scored_item["_dimension_weights"] = result["dimension_weights"]
            scored_items.append(scored_item)

        # 按总分降序排列
        scored_items.sort(key=lambda x: x.get("_total_score", 0), reverse=True)
        return scored_items

    def get_top_news(self, news_items: List[Dict[str, Any]],
                     top_n: int = 20) -> List[Dict[str, Any]]:
        """
        获取评分最高的新闻

        Args:
            news_items: 新闻条目列表
            top_n: 返回前N条

        Returns:
            List[Dict]: 评分最高的N条新闻
        """
        scored = self.score_news_batch(news_items)
        return scored[:top_n]


# 全局实例
_scorer_instance = None


def get_news_scorer():
    """获取新闻评分器实例（单例模式）"""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = NewsScorer()
    return _scorer_instance


if __name__ == "__main__":
    # 测试代码
    scorer = get_news_scorer()

    test_news = [
        {
            "title": "科技创新推动经济高质量发展新篇章",
            "content": "近年来，中国科技创新取得重大突破。在人工智能、量子计算、生物医药等领域，一批重大科技成果相继问世。这些突破性进展不仅推动了经济高质量发展，也为全球科技进步贡献了中国智慧。",
            "source": "人民日报",
            "hot_score": 850,
            "published": "2025-04-25 08:30:00"
        },
        {
            "title": "全球AI治理框架讨论持续升温，各国分歧明显",
            "content": "在近日举行的全球AI安全峰会上，各国代表就人工智能监管问题展开激烈辩论。美国、欧盟和中国在AI治理思路上存在显著分歧，争议焦点包括数据跨境流动、算法透明度等核心问题。专家分析认为，建立统一的全球AI治理框架仍面临诸多挑战。",
            "source": "Reuters",
            "hot_score": 720,
            "published": "2025-04-25 10:15:00"
        }
    ]

    print("=" * 60)
    print("新闻六维评分系统测试")
    print("=" * 60)

    for item in test_news:
        result = scorer.get_dimension_scores(item)
        print(f"\n--- {item['title'][:30]}... ---")
        print(f"来源: {item['source']}")
        print(f"总分: {result['total_score']}/100")
        for dim, score in result['scores'].items():
            label = result['dimension_labels'][dim]
            weight = result['dimension_weights'][dim]
            detail = result['details'][dim][:50]
            print(f"  {label}: {score}分 (权重{weight:.0%}) - {detail}")
        print()

    # 测试批量评分
    scored = scorer.score_news_batch(test_news)
    print("批量评分排序:")
    for item in scored:
        print(f"  {item['title'][:30]}: {item['_total_score']}分")
