#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词云服务类 - 从新闻中提取关键词并生成词云数据
"""

import re
from typing import List, Dict, Any


class WordCloudService:
    """词云服务类，用于从新闻中提取关键词"""

    def __init__(self):
        # 常见停用词
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这',
            'the', 'and', 'of', 'to', 'in', 'a', 'is', 'that', 'for',
            'it', 'as', 'was', 'with', 'on', 'at', 'by', 'an', 'be',
            'this', 'which', 'or', 'from', 'but', 'not', 'are', 'they',
            'his', 'her', 'their', 'its', 'we', 'you', 'he', 'she',
            'for', 'news', 'report', 'says', 'said', 'new', 'more',
            'after', 'before', 'when', 'where', 'who', 'what', 'how',
            'can', 'will', 'would', 'could', 'should', 'may', 'might',
            'has', 'have', 'had', 'been', 'being', 'having', 'do', 'does',
            'did', 'make', 'made', 'get', 'got', 'go', 'goes', 'went',
            'come', 'comes', 'came', 'take', 'takes', 'took', 'see', 'sees',
            'saw', 'know', 'knows', 'knew', 'think', 'thinks', 'thought',
            'want', 'wants', 'wanted', 'use', 'uses', 'used', 'work',
            'works', 'worked', 'call', 'calls', 'called', 'try', 'tries',
            'tried', 'ask', 'asks', 'asked', 'need', 'needs', 'needed',
            'feel', 'feels', 'felt', 'become', 'becomes', 'became',
            'leave', 'leaves', 'left', 'put', 'puts', 'mean', 'means',
            'meant', 'keep', 'keeps', 'kept', 'let', 'lets', 'begin',
            'begins', 'began', 'seem', 'seems', 'seemed', 'help', 'helps',
            'helped', 'talk', 'talks', 'talked', 'turn', 'turns', 'turned',
            'start', 'starts', 'started', 'show', 'shows', 'showed',
            'hear', 'hears', 'heard', 'play', 'plays', 'played', 'run',
            'runs', 'ran', 'move', 'moves', 'moved', 'live', 'lives',
            'lived', 'believe', 'believes', 'believed', 'bring', 'brings',
            'brought', 'happen', 'happens', 'happened', 'write', 'writes',
            'wrote', 'provide', 'provides', 'provided', 'sit', 'sits',
            'sat', 'stand', 'stands', 'stood', 'lose', 'loses', 'lost',
            'pay', 'pays', 'paid', 'meet', 'meets', 'met', 'include',
            'includes', 'included', 'continue', 'continues', 'continued',
            'set', 'sets', 'learn', 'learns', 'learned', 'change',
            'changes', 'changed', 'lead', 'leads', 'led', 'understand',
            'understands', 'understood', 'watch', 'watches', 'watched',
            'follow', 'follows', 'followed', 'stop', 'stops', 'stopped',
            'create', 'creates', 'created', 'speak', 'speaks', 'spoke',
            'read', 'reads', 'spend', 'spends', 'spent', 'grow', 'grows',
            'grew', 'open', 'opens', 'opened', 'walk', 'walks', 'walked',
            'win', 'wins', 'won', 'offer', 'offers', 'offered', 'remember',
            'remembers', 'remembered', 'love', 'loves', 'loved', 'consider',
            'considers', 'considered', 'appear', 'appears', 'appeared',
            'buy', 'buys', 'bought', 'wait', 'waits', 'waited', 'serve',
            'serves', 'served', 'die', 'dies', 'died', 'send', 'sends',
            'sent', 'expect', 'expects', 'expected', 'build', 'builds',
            'built', 'stay', 'stays', 'stayed', 'fall', 'falls', 'fell',
            'cut', 'cuts', 'reach', 'reaches', 'reached', 'kill', 'kills',
            'killed', 'remain', 'remains', 'remained',
        }

    def extract_keywords(self, news_list: List[Dict[str, Any]], top_n: int = 50) -> List[Dict[str, Any]]:
        """从新闻列表中提取关键词，用于词云图

        Args:
            news_list: 新闻列表
            top_n: 返回前N个关键词

        Returns:
            list: 关键词列表，每个元素为 {'word': 词, 'weight': 权重}
        """
        # 统计词频
        word_count = {}

        for news in news_list:
            title = news.get('title', '')
            if not title:
                continue

            # 简单分词（按空格和常见标点符号）
            words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', title)

            for word in words:
                word = word.lower()
                # 过滤停用词和短词
                if len(word) < 2 or word in self.stop_words:
                    continue

                # 统计词频
                word_count[word] = word_count.get(word, 0) + 1

        # 按词频排序
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)

        # 返回前N个关键词
        keywords = []
        for word, count in sorted_words[:top_n]:
            keywords.append({
                'word': word,
                'weight': count
            })

        return keywords


# 全局实例
_word_cloud_service = None


def get_word_cloud_service() -> WordCloudService:
    """获取词云服务实例"""
    global _word_cloud_service
    if _word_cloud_service is None:
        _word_cloud_service = WordCloudService()
    return _word_cloud_service
