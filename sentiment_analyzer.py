#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情感分析模块 - 第四阶段优化迭代3
实现情感倾向分析功能：
1. 中性/积极/消极分类
2. 情感强度分级（0-5级）
3. 情感标签可视化
"""

import re
from typing import Dict, Any, List, Tuple


class SentimentAnalyzer:
    """情感分析器 - 基于关键词的情感分析"""
    
    def __init__(self):
        # 初始化情感词典
        self.positive_words = self._load_positive_words()
        self.negative_words = self._load_negative_words()
        self.intensifiers = self._load_intensifiers()
        self.negations = self._load_negations()
        
    def _load_positive_words(self) -> Dict[str, float]:
        """加载积极情感词汇"""
        # 中文积极词汇（词汇: 权重）
        chinese_positive = {
            '好': 1.0, '优秀': 2.0, '优秀': 2.0, '卓越': 2.5, '出色': 2.0,
            '成功': 1.5, '胜利': 2.0, '赢': 1.5, '胜利': 2.0, '成就': 1.5,
            '快乐': 1.5, '高兴': 1.5, '开心': 1.5, '喜悦': 1.8, '幸福': 2.0,
            '爱': 2.5, '喜欢': 1.5, '热爱': 2.0, '崇拜': 2.0,
            '美丽': 1.5, '漂亮': 1.5, '优美': 1.8, '壮观': 2.0,
            '强大': 1.5, '强大': 1.5, '强大': 1.5, '有力': 1.5,
            '安全': 1.0, '稳定': 1.0, '可靠': 1.2, '信任': 1.5,
            '进步': 1.2, '发展': 1.0, '增长': 1.0, '提升': 1.2,
            '和平': 1.5, '和谐': 1.5, '友好': 1.2, '合作': 1.0,
            '健康': 1.2, '健康': 1.2, '强壮': 1.0, '活力': 1.2,
            '聪明': 1.2, '智慧': 1.5, '明智': 1.2, '机智': 1.2,
            '感谢': 1.5, '感激': 1.8, '感恩': 1.8, '谢谢': 1.5,
            '希望': 1.0, '期待': 1.0, '展望': 1.0, '乐观': 1.5,
            '创新': 1.2, '创造': 1.2, '发明': 1.5, '突破': 2.0,
            '繁荣': 1.5, '富裕': 1.5, '兴旺': 1.5, '昌盛': 1.8,
        }
        
        # 英文积极词汇
        english_positive = {
            'good': 1.0, 'excellent': 2.0, 'great': 1.8, 'awesome': 2.0,
            'success': 1.5, 'victory': 2.0, 'win': 1.5, 'achievement': 1.5,
            'happy': 1.5, 'joy': 1.8, 'pleasure': 1.5, 'delight': 1.8,
            'love': 2.5, 'like': 1.5, 'adore': 2.0, 'cherish': 2.0,
            'beautiful': 1.5, 'pretty': 1.2, 'gorgeous': 2.0, 'stunning': 2.0,
            'strong': 1.5, 'powerful': 1.8, 'mighty': 2.0, 'robust': 1.5,
            'safe': 1.0, 'secure': 1.2, 'stable': 1.0, 'reliable': 1.2,
            'progress': 1.2, 'development': 1.0, 'growth': 1.0, 'improvement': 1.2,
            'peace': 1.5, 'harmony': 1.5, 'friendly': 1.2, 'cooperation': 1.0,
            'healthy': 1.2, 'fit': 1.0, 'strong': 1.0, 'energetic': 1.2,
            'smart': 1.2, 'intelligent': 1.5, 'wise': 1.5, 'clever': 1.2,
            'thank': 1.5, 'grateful': 1.8, 'appreciate': 1.8, 'thanks': 1.5,
            'hope': 1.0, 'expect': 1.0, 'look forward': 1.2, 'optimistic': 1.5,
            'innovation': 1.2, 'creation': 1.2, 'invention': 1.5, 'breakthrough': 2.0,
            'prosperity': 1.5, 'wealthy': 1.5, 'flourish': 1.5, 'thrive': 1.5,
        }
        
        # 合并词典
        positive_words = {}
        positive_words.update(chinese_positive)
        positive_words.update(english_positive)
        
        return positive_words
    
    def _load_negative_words(self) -> Dict[str, float]:
        """加载消极情感词汇"""
        # 中文消极词汇
        chinese_negative = {
            '坏': 1.0, '糟糕': 2.0, '差': 1.5, '恶劣': 2.0,
            '失败': 2.0, '失利': 1.8, '输': 1.5, '败': 1.5,
            '悲伤': 1.8, '难过': 1.5, '伤心': 1.8, '痛苦': 2.0,
            '恨': 2.5, '讨厌': 1.8, '憎恶': 2.5, '厌恶': 2.0,
            '丑陋': 1.5, '难看': 1.2, '丑恶': 1.8, '丑陋': 1.5,
            '弱': 1.0, '脆弱': 1.5, '无力': 1.5, '软弱': 1.2,
            '危险': 2.0, '不安全': 1.8, '威胁': 2.0, '危机': 2.0,
            '衰退': 1.5, '下降': 1.2, '减少': 1.0, '降低': 1.0,
            '冲突': 1.8, '战争': 2.5, '战斗': 2.0, '对抗': 1.8,
            '病': 1.5, '疾病': 1.8, '生病': 1.5, '病毒': 2.0,
            '愚蠢': 1.5, '笨': 1.2, '傻': 1.0, '无知': 1.2,
            '抱怨': 1.2, '批评': 1.0, '指责': 1.5, '谴责': 2.0,
            '失望': 1.8, '绝望': 2.5, '悲观': 1.5, '沮丧': 1.8,
            '问题': 1.0, '困难': 1.2, '挑战': 1.0, '障碍': 1.2,
            '贫穷': 1.5, '贫困': 1.8, '缺乏': 1.2, '不足': 1.0,
            '死亡': 2.5, '去世': 2.0, '牺牲': 2.0, '丧失': 1.8,
            '错误': 1.2, '失误': 1.5, '过错': 1.5, '罪': 2.0,
            '紧张': 1.2, '压力': 1.5, '焦虑': 1.8, '担心': 1.2,
        }
        
        # 英文消极词汇
        english_negative = {
            'bad': 1.0, 'terrible': 2.0, 'poor': 1.5, 'awful': 2.0,
            'failure': 2.0, 'defeat': 1.8, 'lose': 1.5, 'loss': 1.5,
            'sad': 1.8, 'unhappy': 1.5, 'sorrow': 2.0, 'grief': 2.0,
            'hate': 2.5, 'dislike': 1.8, 'detest': 2.5, 'loathe': 2.5,
            'ugly': 1.5, 'unattractive': 1.2, 'hideous': 2.0, 'repulsive': 2.0,
            'weak': 1.0, 'weakness': 1.2, 'powerless': 1.5, 'feeble': 1.2,
            'danger': 2.0, 'dangerous': 2.0, 'threat': 2.0, 'risk': 1.5,
            'decline': 1.5, 'decrease': 1.2, 'reduce': 1.0, 'downturn': 1.5,
            'conflict': 1.8, 'war': 2.5, 'fight': 2.0, 'battle': 2.0,
            'sick': 1.5, 'ill': 1.5, 'disease': 1.8, 'virus': 2.0,
            'stupid': 1.5, 'foolish': 1.2, 'dumb': 1.0, 'ignorant': 1.2,
            'complain': 1.2, 'criticize': 1.0, 'blame': 1.5, 'condemn': 2.0,
            'disappointed': 1.8, 'despair': 2.5, 'pessimistic': 1.5, 'depressed': 2.0,
            'problem': 1.0, 'difficulty': 1.2, 'challenge': 1.0, 'obstacle': 1.2,
            'poor': 1.5, 'poverty': 1.8, 'lack': 1.2, 'shortage': 1.0,
            'death': 2.5, 'die': 2.0, 'dead': 2.0, 'loss': 1.8,
            'wrong': 1.2, 'mistake': 1.5, 'error': 1.5, 'fault': 1.2,
            'stress': 1.5, 'pressure': 1.5, 'anxiety': 1.8, 'worry': 1.2,
        }
        
        # 合并词典
        negative_words = {}
        negative_words.update(chinese_negative)
        negative_words.update(english_negative)
        
        return negative_words
    
    def _load_intensifiers(self) -> Dict[str, float]:
        """加载程度副词（增强情感强度）"""
        intensifiers = {
            # 中文程度副词
            '非常': 1.5, '极其': 2.0, '十分': 1.5, '特别': 1.5,
            '极其': 2.0, '极端': 2.0, '极度': 2.0, '超级': 1.8,
            '很': 1.2, '太': 1.5, '相当': 1.2, '颇为': 1.2,
            '稍微': 0.8, '有点': 0.8, '略微': 0.8, '稍稍': 0.8,
            # 英文程度副词
            'very': 1.5, 'extremely': 2.0, 'highly': 1.5, 'especially': 1.5,
            'exceptionally': 2.0, 'incredibly': 2.0, 'absolutely': 2.0, 'super': 1.8,
            'quite': 1.2, 'rather': 1.2, 'fairly': 1.0, 'somewhat': 0.8,
            'slightly': 0.8, 'a bit': 0.8, 'a little': 0.8, 'moderately': 1.0,
        }
        return intensifiers
    
    def _load_negations(self) -> set:
        """加载否定词"""
        negations = {
            # 中文否定词
            '不', '没', '没有', '未', '非', '无', '勿', '别',
            '否', '莫', '休', '毋', '未尝', '未曾', '不会', '不能',
            # 英文否定词
            'not', "n't", 'no', 'never', 'none', 'nothing', 'nobody',
            'nowhere', 'neither', 'nor', 'without', 'lack', 'fail',
        }
        return negations
    
    def analyze_sentiment(self, text: str, title: str = "") -> Dict[str, Any]:
        """
        分析文本情感
        
        Args:
            text: 新闻正文
            title: 新闻标题（可选）
            
        Returns:
            Dict containing:
                - sentiment: 情感分类 ('positive', 'negative', 'neutral')
                - intensity: 情感强度 (0-5)
                - score: 情感得分 (-5 to 5)
                - confidence: 置信度 (0-1)
                - positive_words: 检测到的积极词汇
                - negative_words: 检测到的消极词汇
                - sentiment_label: 情感标签（可视化用）
        """
        if not text:
            text = title
            
        combined_text = f"{title} {text}" if title else text
        
        # 预处理文本
        words = self._preprocess_text(combined_text)
        
        # 分析情感
        sentiment_result = self._analyze_words_sentiment(words)
        
        # 确定情感分类
        sentiment, confidence = self._determine_sentiment(sentiment_result)
        
        # 计算情感强度 (0-5)
        intensity = self._calculate_intensity(sentiment_result, sentiment)
        
        # 计算情感得分 (-5 to 5)
        score = self._calculate_score(sentiment_result)
        
        # 生成情感标签
        sentiment_label = self._generate_sentiment_label(sentiment, intensity)
        
        return {
            "success": True,
            "sentiment": sentiment,
            "intensity": intensity,
            "score": score,
            "confidence": confidence,
            "positive_words": sentiment_result["positive_words"],
            "negative_words": sentiment_result["negative_words"],
            "sentiment_label": sentiment_label,
            "text_preview": text[:100] + "..." if len(text) > 100 else text
        }
    
    def _preprocess_text(self, text: str) -> List[str]:
        """预处理文本：分词、转换为小写"""
        if not text:
            return []
        
        # 简单的分词：分割单词和中文词汇
        # 匹配中文字符、英文字母、数字
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', text.lower())
        
        return words
    
    def _analyze_words_sentiment(self, words: List[str]) -> Dict[str, Any]:
        """分析词汇情感"""
        positive_words_found = []
        negative_words_found = []
        total_positive_score = 0.0
        total_negative_score = 0.0
        
        # 检查否定词和程度副词的影响
        for i, word in enumerate(words):
            # 检查是否为程度副词
            intensifier_weight = self.intensifiers.get(word, 1.0)
            
            # 检查是否为否定词
            is_negated = False
            # 检查前面几个词是否有否定词
            lookback = min(i, 3)
            for j in range(1, lookback + 1):
                if words[i - j] in self.negations:
                    is_negated = True
                    break
            
            # 检查积极词汇
            if word in self.positive_words:
                score = self.positive_words[word] * intensifier_weight
                if is_negated:
                    # 否定词反转情感
                    score = -score * 0.5  # 否定后的消极情感强度减半
                    negative_words_found.append(f"{word}(negated)")
                    total_negative_score += abs(score)
                else:
                    positive_words_found.append(word)
                    total_positive_score += score
            
            # 检查消极词汇
            elif word in self.negative_words:
                score = self.negative_words[word] * intensifier_weight
                if is_negated:
                    # 否定词反转情感
                    score = -score * 0.5  # 否定后的积极情感强度减半
                    positive_words_found.append(f"{word}(negated)")
                    total_positive_score += abs(score)
                else:
                    negative_words_found.append(word)
                    total_negative_score += score
        
        return {
            "positive_words": positive_words_found,
            "negative_words": negative_words_found,
            "positive_score": total_positive_score,
            "negative_score": total_negative_score,
            "total_words": len(words)
        }
    
    def _determine_sentiment(self, sentiment_result: Dict[str, Any]) -> Tuple[str, float]:
        """确定情感分类和置信度"""
        positive_score = sentiment_result["positive_score"]
        negative_score = sentiment_result["negative_score"]
        total_words = sentiment_result["total_words"]
        
        if total_words == 0:
            return "neutral", 0.5
        
        # 计算净情感得分
        net_score = positive_score - negative_score
        
        # 确定情感分类
        if net_score > 0.5:
            sentiment = "positive"
            confidence = min(net_score / (positive_score + 1), 1.0)
        elif net_score < -0.5:
            sentiment = "negative"
            confidence = min(abs(net_score) / (negative_score + 1), 1.0)
        else:
            sentiment = "neutral"
            # 中性置信度基于情感得分的接近程度
            confidence = 1.0 - min(abs(net_score), 1.0)
        
        return sentiment, confidence
    
    def _calculate_intensity(self, sentiment_result: Dict[str, Any], sentiment: str) -> int:
        """计算情感强度 (0-5)"""
        if sentiment == "neutral":
            return 0
        
        if sentiment == "positive":
            score = sentiment_result["positive_score"]
        else:  # negative
            score = sentiment_result["negative_score"]
        
        # 根据得分计算强度
        if score < 1.0:
            intensity = 1
        elif score < 2.0:
            intensity = 2
        elif score < 3.0:
            intensity = 3
        elif score < 4.0:
            intensity = 4
        else:
            intensity = 5
        
        return min(intensity, 5)  # 确保不超过5
    
    def _calculate_score(self, sentiment_result: Dict[str, Any]) -> float:
        """计算情感得分 (-5 to 5)"""
        positive_score = sentiment_result["positive_score"]
        negative_score = sentiment_result["negative_score"]
        
        # 计算净得分并归一化到-5到5范围
        net_score = positive_score - negative_score
        
        # 简单的归一化：使用tanh函数
        normalized_score = self._tanh_normalize(net_score, scale=2.0)
        
        # 限制在-5到5之间
        return max(min(normalized_score, 5.0), -5.0)
    
    def _tanh_normalize(self, value: float, scale: float = 1.0) -> float:
        """使用tanh函数归一化值"""
        import math
        return scale * math.tanh(value / scale)
    
    def _generate_sentiment_label(self, sentiment: str, intensity: int) -> str:
        """生成情感标签"""
        if sentiment == "neutral":
            return "中性"
        
        intensity_labels = {
            1: "轻微",
            2: "一般",
            3: "较强",
            4: "强烈",
            5: "极强"
        }
        
        intensity_label = intensity_labels.get(intensity, "")
        
        if sentiment == "positive":
            return f"{intensity_label}积极"
        else:  # negative
            return f"{intensity_label}消极"


# 全局实例
_analyzer_instance = None

def get_sentiment_analyzer():
    """获取情感分析器实例（单例模式）"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = SentimentAnalyzer()
    return _analyzer_instance


def analyze_sentiment_from_news(news_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    从新闻项中分析情感（方便函数）
    
    Args:
        news_item: 新闻字典，包含title, source, content等字段
        
    Returns:
        情感分析结果
    """
    analyzer = get_sentiment_analyzer()
    
    title = news_item.get('title', '')
    # 尝试获取内容，如果没有则使用标题
    content = news_item.get('content', '') or news_item.get('description', '') or title
    
    return analyzer.analyze_sentiment(content, title)


if __name__ == "__main__":
    # 测试代码
    analyzer = SentimentAnalyzer()
    
    test_cases = [
        "今天天气非常好，阳光明媚，心情特别愉快！",
        "这是一个糟糕的消息，让人非常失望和难过。",
        "公司发布了新的产品，市场反应一般，没有特别的好评也没有差评。",
        "The project was a complete failure and everyone is extremely disappointed.",
        "I absolutely love this beautiful and wonderful experience! It's incredibly amazing.",
        "Not bad, but not great either. It's just okay.",
    ]
    
    print("=" * 60)
    print("情感分析器测试")
    print("=" * 60)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n测试 {i}:")
        print(f"  原文: {text}")
        result = analyzer.analyze_sentiment(text)
        print(f"  情感: {result['sentiment']} ({result['sentiment_label']})")
        print(f"  强度: {result['intensity']}/5")
        print(f"  得分: {result['score']:.2f}")
        print(f"  置信度: {result['confidence']:.2%}")
        
        if result['positive_words']:
            print(f"  积极词汇: {', '.join(result['positive_words'][:5])}")
        
        if result['negative_words']:
            print(f"  消极词汇: {', '.join(result['negative_words'][:5])}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)