#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻摘要生成模块 - 第四阶段优化迭代2
实现智能摘要功能：
1. 国内新闻→中文摘要（50-100字）
2. 国际新闻→英文摘要（原文）
3. TextRank摘要算法
"""

import re
from typing import List, Dict, Any, Optional
import math
from collections import defaultdict


class NewsSummarizer:
    """新闻摘要生成器 - 基于TextRank算法"""
    
    def __init__(self):
        # 停用词列表（中文和英文）
        self.stopwords = self._load_stopwords()
        
    def _load_stopwords(self) -> set:
        """加载停用词"""
        # 基础停用词（实际应用中可以从文件加载更多）
        stopwords = set([
            # 中文停用词
            '的', '了', '在', '是', '和', '与', '或', '有', '就', '都', '而', '及', '着', '呢', '吗', '吧', '啊', '呀',
            '这', '那', '哪', '什么', '怎么', '为什么', '如何', '我们', '你们', '他们', '她们', '它们', '自己',
            '也', '又', '还', '更', '最', '太', '很', '非常', '特别', '极其', '比较', '稍微', '几乎', '大约',
            '已经', '曾经', '正在', '将要', '可以', '可能', '应该', '必须', '需要', '能够', '愿意', '敢',
            '一个', '一些', '一种', '一点', '一些', '许多', '几个', '少量', '大量', '全部', '部分', '整个',
            # 英文停用词
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what', 'which', 'this', 'that', 'these', 'those',
            'then', 'just', 'so', 'than', 'such', 'both', 'either', 'neither', 'all', 'any', 'most', 'other', 'some',
            'few', 'many', 'lot', 'lots', 'several', 'various', 'each', 'every', 'either', 'neither', 'one', 'ones',
            'to', 'of', 'in', 'for', 'on', 'by', 'at', 'with', 'about', 'against', 'between', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'from', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'can', 'will', 'just', 'should', 'now'
        ])
        return stopwords
    
    def _preprocess_text(self, text: str, language: str = 'zh') -> List[str]:
        """预处理文本：分词、清洗、去除停用词"""
        if not text:
            return []
            
        # 根据语言选择分词方式（简化版，实际应用可以使用jieba等分词工具）
        if language == 'zh':
            # 中文分词：简单的基于正则的分词
            words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z0-9]+', text)
        else:
            # 英文分词：按单词分割
            words = re.findall(r'\b[a-zA-Z]+\b', text)
            
        # 转换为小写并去除停用词
        words = [word.lower() for word in words if word.lower() not in self.stopwords]
        
        return words
    
    def _build_sentence_similarity_matrix(self, sentences: List[str], language: str = 'zh') -> List[List[float]]:
        """构建句子相似度矩阵"""
        n = len(sentences)
        if n == 0:
            return []
            
        # 预处理每个句子
        sentence_words = [self._preprocess_text(sent, language) for sent in sentences]
        
        # 构建相似度矩阵
        similarity_matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                elif i < j:
                    # 计算余弦相似度
                    words_i = set(sentence_words[i])
                    words_j = set(sentence_words[j])
                    
                    if not words_i or not words_j:
                        similarity = 0.0
                    else:
                        intersection = len(words_i.intersection(words_j))
                        similarity = intersection / (math.log(len(words_i)) + math.log(len(words_j)) + 1e-10)
                    
                    similarity_matrix[i][j] = similarity
                    similarity_matrix[j][i] = similarity
        
        return similarity_matrix
    
    def _textrank_score(self, similarity_matrix: List[List[float]], damping: float = 0.85, 
                       max_iter: int = 100, tol: float = 1e-4) -> List[float]:
        """计算TextRank得分"""
        n = len(similarity_matrix)
        if n == 0:
            return []
            
        # 初始化得分
        scores = [1.0 / n] * n
        
        for _ in range(max_iter):
            prev_scores = scores.copy()
            
            for i in range(n):
                # 计算当前句子的新得分
                sum_similarity = 0.0
                for j in range(n):
                    if i != j and sum(similarity_matrix[j]) > 0:
                        sum_similarity += similarity_matrix[j][i] / sum(similarity_matrix[j]) * prev_scores[j]
                
                scores[i] = (1 - damping) / n + damping * sum_similarity
            
            # 检查收敛
            diff = sum(abs(scores[i] - prev_scores[i]) for i in range(n))
            if diff < tol:
                break
        
        return scores
    
    def summarize_text(self, text: str, language: str = 'zh', summary_length: int = 100) -> str:
        """
        生成文本摘要
        
        Args:
            text: 原始文本
            language: 语言 ('zh' 或 'en')
            summary_length: 摘要目标长度（字符数）
            
        Returns:
            生成的摘要
        """
        if not text:
            return ""
            
        # 分割句子
        if language == 'zh':
            # 中文句子分割
            sentences = re.split(r'[。！？；\.!?;]', text)
        else:
            # 英文句子分割
            sentences = re.split(r'[\.!?;]', text)
            
        sentences = [sent.strip() for sent in sentences if sent.strip()]
        
        if len(sentences) <= 2:
            # 句子太少，直接返回前几个句子
            summary = ' '.join(sentences)
            return self._truncate_summary(summary, summary_length, language)
        
        # 构建相似度矩阵
        similarity_matrix = self._build_sentence_similarity_matrix(sentences, language)
        
        if not similarity_matrix:
            return self._truncate_summary(text, summary_length, language)
        
        # 计算TextRank得分
        scores = self._textrank_score(similarity_matrix)
        
        # 根据得分排序句子
        ranked_sentences = sorted(zip(scores, sentences), reverse=True)
        
        # 选择最重要的句子，直到达到目标长度
        selected_sentences = []
        current_length = 0
        
        for score, sentence in ranked_sentences:
            sent_length = len(sentence)
            if current_length + sent_length <= summary_length:
                selected_sentences.append(sentence)
                current_length += sent_length
            else:
                # 如果摘要还不够长，可以添加部分句子
                remaining = summary_length - current_length
                if remaining > 20:  # 如果剩余空间较大
                    truncated = sentence[:remaining] + ('...' if language == 'zh' else '...')
                    selected_sentences.append(truncated)
                break
        
        # 按原文顺序排序
        selected_sentences = [sent for sent in sentences if sent in selected_sentences]
        
        # 生成摘要
        if language == 'zh':
            summary = '。'.join(selected_sentences)
            if summary and not summary.endswith('。'):
                summary += '。'
        else:
            summary = '. '.join(selected_sentences)
            if summary and not summary.endswith('.'):
                summary += '.'
        
        return self._truncate_summary(summary, summary_length, language)
    
    def _truncate_summary(self, summary: str, max_length: int, language: str) -> str:
        """截断摘要到指定长度"""
        if len(summary) <= max_length:
            return summary
            
        if language == 'zh':
            return summary[:max_length] + '...'
        else:
            return summary[:max_length] + '...'
    
    def summarize_news(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成新闻摘要
        
        Args:
            news_item: 新闻字典，包含title, source, content, region等字段
            
        Returns:
            摘要结果
        """
        try:
            title = news_item.get('title', '')
            # 尝试获取内容
            content = news_item.get('content', '') or news_item.get('description', '') or title
            
            # 如果没有足够的内容，返回标题作为摘要
            if not content or len(content.strip()) < 20:
                return {
                    "success": True,
                    "summary": title[:100] + ('...' if len(title) > 100 else ''),
                    "language": "zh",
                    "algorithm": "title_only",
                    "original_length": len(content) if content else 0,
                    "summary_length": min(len(title), 100)
                }
            
            # 判断新闻语言和类型
            region = news_item.get('region', '')
            source = news_item.get('source', '').lower()
            
            # 判断是否为国际新闻
            is_international = self._is_international_news(region, source, content)
            
            if is_international:
                # 国际新闻：生成英文摘要
                language = 'en'
                # 如果内容主要是中文，可能误判，检查一下
                if self._is_chinese_content(content):
                    language = 'zh'
            else:
                # 国内新闻：生成中文摘要
                language = 'zh'
            
            # 根据语言选择摘要长度
            if language == 'zh':
                target_length = 100  # 中文摘要目标100字
            else:
                target_length = 200  # 英文摘要目标200字符
            
            # 生成摘要
            summary = self.summarize_text(content, language, target_length)
            
            # 如果摘要太短，使用标题补充
            if len(summary) < 30:
                if language == 'zh':
                    summary = title + '。' + summary
                else:
                    summary = title + '. ' + summary
            
            return {
                "success": True,
                "summary": summary,
                "language": language,
                "algorithm": "textrank",
                "original_length": len(content),
                "summary_length": len(summary),
                "is_international": is_international
            }
            
        except Exception as e:
            # 出错时返回标题作为摘要
            title = news_item.get('title', '')
            return {
                "success": False,
                "summary": title[:100] + ('...' if len(title) > 100 else ''),
                "language": "zh",
                "algorithm": "error_fallback",
                "error": str(e),
                "original_length": 0,
                "summary_length": min(len(title), 100)
            }
    
    def _is_international_news(self, region: str, source: str, content: str) -> bool:
        """判断是否为国际新闻"""
        # 根据地区判断
        international_regions = ['北美', '欧洲', '亚洲', '中东', '全球', '其他']
        if region in international_regions:
            return True
        
        # 根据来源判断
        international_sources = ['bbc', 'reuters', 'npr', 'cnn', 'fox', 'ap', 'bloomberg', 
                                 'guardian', 'independent', 'al jazeera']
        if any(source_keyword in source for source_keyword in international_sources):
            return True
        
        # 根据内容判断：如果英文内容比例高
        if self._english_content_ratio(content) > 0.5:
            return True
        
        return False
    
    def _is_chinese_content(self, text: str) -> bool:
        """判断内容是否主要是中文"""
        if not text:
            return False
        
        # 统计中文字符数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        total_chars = len(text.strip())
        
        if total_chars == 0:
            return False
        
        return chinese_chars / total_chars > 0.3
    
    def _english_content_ratio(self, text: str) -> float:
        """计算英文内容比例"""
        if not text:
            return 0.0
        
        # 统计英文字母数
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = len(re.findall(r'\S', text))  # 非空白字符
        
        if total_chars == 0:
            return 0.0
        
        return english_chars / total_chars


# 全局实例
_summarizer_instance = None

def get_summarizer():
    """获取摘要生成器实例（单例模式）"""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = NewsSummarizer()
    return _summarizer_instance


def generate_summary_for_news(news_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    为新闻项生成摘要（方便函数）
    
    Args:
        news_item: 新闻字典，包含title, source, content等字段
        
    Returns:
        摘要结果
    """
    summarizer = get_summarizer()
    return summarizer.summarize_news(news_item)


if __name__ == "__main__":
    # 测试代码
    summarizer = NewsSummarizer()
    
    test_cases = [
        {
            "title": "习近平主席在北京会见美国总统拜登",
            "content": "习近平主席在北京人民大会堂会见美国总统拜登。双方就中美关系和国际地区问题深入交换意见。习近平强调，中美两国应该相互尊重、和平共处、合作共赢。拜登表示，美国致力于与中国保持沟通，妥善管控分歧。会谈在友好、坦诚的气氛中进行。",
            "source": "人民日报",
            "region": "北京"
        },
        {
            "title": "China and US agree to strengthen climate cooperation",
            "content": "Chinese President Xi Jinping and US President Joe Biden have agreed to strengthen cooperation on climate change during their meeting in Beijing. Both leaders acknowledged the importance of addressing global warming and pledged to work together on reducing carbon emissions. The agreement marks a positive step in US-China relations amid ongoing tensions over trade and technology.",
            "source": "Reuters",
            "region": "北美"
        },
        {
            "title": "俄罗斯宣布成功试射新型洲际弹道导弹",
            "content": "俄罗斯国防部宣布，俄罗斯成功试射了新型洲际弹道导弹。该导弹能够携带多个核弹头，射程覆盖全球。俄罗斯总统普京观看了试射过程并表示，这是俄罗斯国防力量的重要进展。西方国家对此表示关注，担心这会加剧国际紧张局势。",
            "source": "塔斯社",
            "region": "欧洲"
        }
    ]
    
    print("=" * 60)
    print("新闻摘要生成器测试")
    print("=" * 60)
    
    for i, news in enumerate(test_cases, 1):
        print(f"\n测试 {i}:")
        print(f"  标题: {news['title']}")
        print(f"  来源: {news['source']}, 地区: {news['region']}")
        
        result = summarizer.summarize_news(news)
        
        print(f"  成功: {result['success']}")
        print(f"  语言: {result['language']}")
        print(f"  算法: {result['algorithm']}")
        print(f"  摘要: {result['summary']}")
        print(f"  原文长度: {result['original_length']}, 摘要长度: {result['summary_length']}")
        print(f"  是否国际新闻: {result.get('is_international', 'N/A')}")
        
        if 'error' in result:
            print(f"  错误: {result['error']}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)