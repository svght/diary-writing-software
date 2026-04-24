#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体关系图谱模块 - 构建新闻实体关系图谱
使用SQLite数据库统一存储
"""

import json
import os
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
from database import get_database

# 尝试导入networkx，如果不可用则使用纯Python实现
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


class EntityGraph:
    """实体关系图谱 - 管理新闻实体及其关系（数据库版）"""
    
    def __init__(self):
        self.db = get_database()
    
    def add_entity(self, name: str, entity_type: str, properties: Dict = None):
        """添加或更新实体节点"""
        self.db.add_entity(name, entity_type, properties)
    
    def add_relation(self, source_name: str, target_name: str, 
                     relation_type: str = "co_occur", news_id: str = ""):
        """添加实体关系"""
        self.db.add_relation(source_name, target_name, relation_type, news_id)
    
    def process_news(self, entities: Dict, news_id: str = ""):
        """处理一条新闻的实体关系"""
        all_entities = []
        
        # 添加人物实体
        for person in entities.get("persons", []):
            name = person.get("name", "")
            if name:
                self.add_entity(name, "person", {"position": person.get("position", "")})
                all_entities.append(name)
        
        # 添加国家/地点实体
        for country in entities.get("countries", []):
            self.add_entity(country, "country")
            all_entities.append(country)
        
        # 添加组织实体
        for org in entities.get("organizations", []):
            self.add_entity(org, "organization")
            all_entities.append(org)
        
        # 添加事件实体
        for event in entities.get("events", []):
            self.add_entity(event, "event")
            all_entities.append(event)
        
        # 建立共现关系
        for i in range(len(all_entities)):
            for j in range(i + 1, len(all_entities)):
                self.add_relation(all_entities[i], all_entities[j], "co_occur", news_id)
    
    def get_entity_detail(self, entity_name: str) -> Dict:
        """获取单个实体详情"""
        entity_id = self.db.get_entity_id(entity_name)
        if not entity_id:
            return {"success": False, "error": "实体不存在"}
        
        detail = self.db.get_entity_detail(entity_id)
        if not detail:
            return {"success": False, "error": "实体不存在"}
        
        return {
            "success": True,
            "entity": detail,
            "related_entities": detail.get("related_entities", [])[:20],
            "relation_count": len(detail.get("related_entities", []))
        }
    
    def get_full_graph(self, min_weight: int = 1) -> Dict:
        """获取全量图谱数据"""
        return self.db.get_full_graph(min_weight)
    
    def search_entities(self, keyword: str) -> List[Dict]:
        """搜索实体"""
        return self.db.search_entities(keyword)
    
    def get_entity_statistics(self) -> Dict:
        """获取实体统计信息"""
        return self.db.get_entity_statistics()


class EntityExtractor:
    """增强实体提取器 - 提取人物、组织、地点、事件"""
    
    # 常见组织关键词
    ORGANIZATION_KEYWORDS = [
        '公司', '集团', '银行', '基金', '委员会', '协会', '组织', '联盟',
        '机构', '大学', '学院', '研究所', '医院', '政府', '部门',
        '局', '部', '委', '办', '中心', '社', '院', '会',
        'Inc', 'Corp', 'LLC', 'Ltd', 'Group', 'Bank', 'Fund',
        'University', 'Institute', 'Hospital', 'Association', 'Organization'
    ]
    
    # 已知组织名称
    KNOWN_ORGANIZATIONS = {
        '联合国', '世界卫生组织', '世卫组织', '世界贸易组织', '世贸组织',
        '国际货币基金组织', '世界银行', '北约', '欧盟', '欧佩克',
        '国际奥委会', '红十字会', '国际法院',
        'UN', 'WHO', 'WTO', 'IMF', 'NATO', 'EU', 'OPEC',
        'Google', 'Apple', 'Microsoft', 'Amazon', 'Meta', 'Tesla',
        '阿里巴巴', '腾讯', '百度', '华为', '字节跳动', '京东', '拼多多',
        '中国石油', '中国石化', '工商银行', '建设银行', '农业银行', '中国银行'
    }
    
    # 事件关键词模式
    EVENT_PATTERNS = [
        r'(?:召开|举行|举办)\s*[^。，；]{2,30}(?:会议|峰会|论坛|大会|仪式)',
        r'(?:发生|爆发)\s*[^。，；]{2,30}(?:事件|事故|冲突|战争|危机|灾难|疫情|暴乱)',
        r'(?:签署|达成|签订)\s*[^。，；]{2,30}(?:协议|条约|协定|合同)',
        r'(?:启动|开展|实施)\s*[^。，；]{2,30}(?:计划|项目|工程|行动|活动)',
        r'(?:发射|升空|登陆)\s*[^。，；]{2,30}(?:卫星|飞船|探测器)',
        r'(?:举行|开始|结束)\s*[^。，；]{2,30}(?:选举|投票|公投)',
        r'(?:发布|公布|出台)\s*[^。，；]{2,30}(?:政策|法规|法律|规定|报告)',
    ]
    
    def __init__(self):
        # 从新闻分析器继承人物和国家的提取
        from news_analyzer import get_analyzer
        self.news_analyzer = get_analyzer()
        
        # 编译事件正则
        self.event_regexes = [re.compile(p) for p in self.EVENT_PATTERNS]
    
    def extract_all(self, text: str, title: str = "") -> Dict[str, Any]:
        """全面提取实体"""
        combined = f"{title} {text}" if title else text
        if not combined:
            return {"persons": [], "countries": [], "organizations": [], "events": []}
        
        # 1. 使用现有的新闻分析器提取人物和国家
        basic_result = self.news_analyzer.extract_entities(text, title)
        
        # 2. 提取组织
        organizations = self._extract_organizations(combined)
        
        # 3. 提取事件
        events = self._extract_events(combined)
        
        return {
            "persons": basic_result.get("persons", []),
            "countries": basic_result.get("countries", []),
            "organizations": organizations,
            "events": events
        }
    
    def _extract_organizations(self, text: str) -> List[str]:
        """提取组织名称"""
        found = set()
        
        # 已知组织
        for org in self.KNOWN_ORGANIZATIONS:
            if org in text:
                found.add(org)
        
        # 模式匹配：XXX公司/集团/银行等
        org_pattern = re.compile(
            r'[^\s，。；：、（）()""'',，。；：？！\d]{2,10}(?:' + 
            '|'.join(re.escape(kw) for kw in self.ORGANIZATION_KEYWORDS[:10]) + 
            r')'
        )
        for match in org_pattern.finditer(text):
            org_name = match.group().strip()
            if org_name and len(org_name) <= 20:
                found.add(org_name)
        
        return list(found)
    
    def _extract_events(self, text: str) -> List[str]:
        """提取事件名称"""
        found = set()
        
        for regex in self.event_regexes:
            for match in regex.finditer(text):
                event_text = match.group().strip()
                if event_text and len(event_text) <= 30:
                    found.add(event_text)
        
        return list(found)


# 全局实例
_graph_instance = None
_extractor_instance = None


def get_entity_graph():
    """获取实体图谱实例（单例）"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = EntityGraph()
    return _graph_instance


def get_entity_extractor():
    """获取实体提取器实例（单例）"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = EntityExtractor()
    return _extractor_instance


def process_news_for_graph(news_item: Dict):
    """处理新闻更新实体图谱"""
    graph = get_entity_graph()
    extractor = get_entity_extractor()
    
    title = news_item.get('title', '')
    content = news_item.get('content', '') or news_item.get('description', '') or title
    news_id = news_item.get('link', '') or title
    
    entities = extractor.extract_all(content, title)
    graph.process_news(entities, news_id)
    
    # 同时处理事件追踪
    try:
        from event_tracker import get_event_tracker
        tracker = get_event_tracker()
        tracker.process_news(news_item, entities)
    except Exception as e:
        print(f"事件追踪失败: {e}")
    
    return entities


if __name__ == "__main__":
    # 测试
    extractor = EntityExtractor()
    test_text = """
    习近平主席在北京人民大会堂会见美国总统拜登，双方就中美关系进行了深入交流。
    联合国秘书长古特雷斯呼吁各国加强合作，共同应对气候变化。
    华为公司发布了最新的5G技术，阿里巴巴集团表示将加大在AI领域的投资。
    世界卫生组织宣布新冠疫情不再构成国际关注的突发公共卫生事件。
    """
    
    result = extractor.extract_all(test_text, "习近平会见拜登")
    print("实体提取结果:")
    print(f"  人物: {[p['name'] for p in result['persons']]}")
    print(f"  国家: {result['countries']}")
    print(f"  组织: {result['organizations']}")
    print(f"  事件: {result['events']}")
