#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件追踪与关联分析模块
使用SQLite数据库统一存储
"""

import json
import os
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from database import get_database


class EventTracker:
    """事件追踪器 - 聚类相关新闻为事件，追踪发展脉络（数据库版）"""
    
    def __init__(self):
        self.db = get_database()
    
    def _generate_event_id(self) -> str:
        """生成事件ID"""
        counter = self.db.get_event_id_counter()
        return f"EVT{counter + 1:04d}"
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度"""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1[:200], text2[:200]).ratio()
    
    def _extract_keywords(self, text: str) -> set:
        """提取文本关键词"""
        words = set()
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        words.update(chinese_words)
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        words.update(english_words)
        return words
    
    def _find_matching_event(self, news_item: Dict, entities: Dict) -> Optional[str]:
        """查找匹配的已有事件"""
        title = news_item.get('title', '')
        content = news_item.get('content', '') or news_item.get('description', '') or title
        combined_text = f"{title} {content}"
        
        news_keywords = self._extract_keywords(combined_text)
        
        news_entities = set()
        for p in entities.get("persons", []):
            news_entities.add(p.get("name", ""))
        news_entities.update(entities.get("countries", []))
        news_entities.update(entities.get("organizations", []))
        news_entities.update(entities.get("events", []))
        news_entities.discard("")
        
        try:
            pub_date = news_item.get('published', '')
            if pub_date:
                news_time = datetime.strptime(pub_date[:10], '%Y-%m-%d')
            else:
                news_time = datetime.now()
        except Exception:
            news_time = datetime.now()
        
        # 获取已有事件
        events = self.db.get_events_list()
        
        best_match_id = None
        best_match_score = 0
        
        for event in events:
            event_time = datetime.strptime(event["updated_at"][:10], '%Y-%m-%d')
            if abs((news_time - event_time).days) > 30:
                continue
            
            event_entities = set(event.get("entities", []))
            if news_entities and event_entities:
                overlap = len(news_entities & event_entities)
                entity_score = overlap / max(len(news_entities | event_entities), 1)
            else:
                entity_score = 0
            
            event_keywords = set(event.get("keywords", []))
            if news_keywords and event_keywords:
                kw_overlap = len(news_keywords & event_keywords)
                kw_score = kw_overlap / max(len(news_keywords | event_keywords), 1)
            else:
                kw_score = 0
            
            title_sim = self._calculate_similarity(
                title.lower(),
                event.get("summary", "")[:100].lower()
            )
            
            total_score = entity_score * 0.5 + kw_score * 0.3 + title_sim * 0.2
            
            if total_score > best_match_score and total_score > 0.15:
                best_match_score = total_score
                best_match_id = event["id"]
        
        return best_match_id
    
    def process_news(self, news_item: Dict, entities: Dict = None):
        """处理新闻，聚类到事件中"""
        title = news_item.get('title', '')
        content = news_item.get('content', '') or news_item.get('description', '') or title
        combined_text = f"{title} {content}"
        
        keywords = list(self._extract_keywords(combined_text))
        
        entity_list = []
        if entities:
            for p in entities.get("persons", []):
                entity_list.append(p.get("name", ""))
            entity_list.extend(entities.get("countries", []))
            entity_list.extend(entities.get("organizations", []))
            entity_list.extend(entities.get("events", []))
        entity_list = [e for e in entity_list if e]
        
        matched_event_id = self._find_matching_event(news_item, entities or {})
        
        if matched_event_id:
            # 获取已有事件
            event = self.db.get_event_by_id(matched_event_id)
            if event:
                # 更新事件信息
                existing_titles = {n["title"] for n in event.get("news", [])}
                if title not in existing_titles:
                    # 关联新闻到事件
                    news_entry = {
                        "title": title,
                        "link": news_item.get('link', ''),
                        "source": news_item.get('source', ''),
                        "published": news_item.get('published', ''),
                        "entities": entity_list,
                        "sentiment": news_item.get('_sentiment', 'neutral')
                    }
                    
                    # 找新闻ID
                    try:
                        db_news = self.db.get_all_news(limit=100)
                        news_id = None
                        for n in db_news:
                            if n['title'] == title:
                                news_id = n['id']
                                break
                        if news_id:
                            self.db.link_news_to_event(matched_event_id, news_id)
                    except Exception:
                        pass
                    
                    # 更新事件摘要
                    summary = event.get("summary", "") or title[:100]
                    new_count = event.get("news_count", 0) + 1
                    
                    # 确定状态
                    if new_count <= 3:
                        status = "emerging"
                    elif new_count <= 10:
                        status = "active"
                    else:
                        status = "declining"
                    
                    all_keywords = list(set(event.get("keywords", []) + keywords))
                    
                    self.db.save_event(
                        matched_event_id, summary, status,
                        all_keywords[:20], list(set(event.get("entities", []) + entity_list))
                    )
                    
                    # 更新峰值
                    peak = max(new_count, event.get("peak_count", 1))
                    self.db.update_event_status(matched_event_id, status, peak)
        else:
            # 创建新事件
            event_id = self._generate_event_id()
            status = "emerging"
            
            self.db.save_event(
                event_id, title[:100], status,
                keywords[:20], entity_list
            )
            
            # 关联新闻
            try:
                db_news = self.db.get_all_news(limit=100)
                for n in db_news:
                    if n['title'] == title:
                        self.db.link_news_to_event(event_id, n['id'])
                        break
            except Exception:
                pass
    
    def get_event_list(self, status: str = "all", limit: int = 20) -> Dict:
        """获取事件列表"""
        events = self.db.get_events_list(status if status != "all" else "all", limit)
        
        event_list = []
        for event in events:
            event_list.append({
                "id": event["id"],
                "summary": event["summary"],
                "keywords": event.get("keywords", [])[:5],
                "entities": event.get("entities", [])[:10],
                "news_count": event.get("news_count", 0),
                "status": event.get("status", "emerging"),
                "status_label": self._get_status_label(event.get("status", "emerging")),
                "created": event.get("created_at", ""),
                "last_updated": event.get("updated_at", ""),
                "peak_count": event.get("peak_count", 1)
            })
        
        event_list.sort(key=lambda x: x["last_updated"], reverse=True)
        
        return {
            "success": True,
            "events": event_list[:limit],
            "total": len(event_list),
            "status_filter": status
        }
    
    def get_event_detail(self, event_id: str) -> Dict:
        """获取事件详情"""
        event = self.db.get_event_by_id(event_id)
        if not event:
            return {"success": False, "error": "事件不存在"}
        
        # 格式化新闻条目
        news_list = []
        for n in event.get("news", []):
            news_list.append({
                "title": n["title"],
                "link": n.get("url", "") or n.get("link", ""),
                "source": n.get("source", ""),
                "published": n.get("published_at", "") or n.get("published", ""),
                "entities": event.get("entities", []),
                "sentiment": n.get("sentiment", "neutral")
            })
        
        formatted_event = {
            "id": event["id"],
            "summary": event["summary"],
            "keywords": event.get("keywords", []),
            "entities": event.get("entities", []),
            "news": news_list,
            "news_count": event.get("news_count", len(news_list)),
            "status": event.get("status", "emerging"),
            "status_label": self._get_status_label(event.get("status", "emerging")),
            "created": event.get("created_at", ""),
            "last_updated": event.get("updated_at", ""),
            "peak_count": event.get("peak_count", 1)
        }
        
        return {
            "success": True,
            "event": formatted_event
        }
    
    def get_related_events(self, event_id: str) -> Dict:
        """获取关联事件"""
        event = self.db.get_event_by_id(event_id)
        if not event:
            return {"success": False, "error": "事件不存在"}
        
        event_entities = set(event.get("entities", []))
        event_keywords = set(event.get("keywords", []))
        
        all_events = self.db.get_events_list()
        
        related = []
        for other_event in all_events:
            if other_event["id"] == event_id:
                continue
            
            other_entities = set(other_event.get("entities", []))
            other_keywords = set(other_event.get("keywords", []))
            
            entity_overlap = len(event_entities & other_entities)
            kw_overlap = len(event_keywords & other_keywords)
            
            score = entity_overlap * 2 + kw_overlap * 0.5
            
            if score >= 2:
                related.append({
                    "id": other_event["id"],
                    "summary": other_event["summary"],
                    "news_count": other_event.get("news_count", 0),
                    "status": other_event.get("status", "emerging"),
                    "relevance_score": score,
                    "shared_entities": list(event_entities & other_entities)[:5]
                })
        
        related.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return {
            "success": True,
            "event_id": event_id,
            "related_events": related[:10],
            "count": len(related)
        }
    
    def get_timeline(self, entity_name: str = None, event_id: str = None,
                     start_date: str = None, end_date: str = None) -> Dict:
        """获取时间线数据"""
        timeline_items = []
        
        if event_id:
            event = self.db.get_event_by_id(event_id)
            if not event:
                return {"success": False, "error": "事件不存在"}
            
            for news in event.get("news", []):
                published = news.get("published_at", "") or news.get("published", "")
                if published and len(published) >= 10:
                    date_key = published[:10]
                else:
                    date_key = event.get("created_at", "")[:10]
                
                timeline_items.append({
                    "date": date_key,
                    "title": news["title"],
                    "link": news.get("url", "") or news.get("link", ""),
                    "source": news.get("source", ""),
                    "entities": event.get("entities", [])[:5],
                    "sentiment": news.get("sentiment", "neutral"),
                    "event_id": event_id,
                    "event_summary": event["summary"]
                })
        
        elif entity_name:
            entity_id = self.db.get_entity_id(entity_name)
            if entity_id:
                news_ids = self.db.get_entity_news_ids(entity_name)
                all_events = self.db.get_events_list()
                
                for event in all_events:
                    if entity_name in event.get("entities", []):
                        for news_item in event.get("news", []):
                            published = news_item.get("published_at", "") or news_item.get("published", "")
                            if published and len(published) >= 10:
                                date_key = published[:10]
                            else:
                                date_key = event.get("created_at", "")[:10]
                            
                            timeline_items.append({
                                "date": date_key,
                                "title": news_item["title"],
                                "link": news_item.get("url", "") or news_item.get("link", ""),
                                "source": news_item.get("source", ""),
                                "entities": event.get("entities", [])[:5],
                                "sentiment": news_item.get("sentiment", "neutral"),
                                "event_id": event["id"],
                                "event_summary": event["summary"]
                            })
        else:
            all_events = self.db.get_events_list()
            for event in all_events:
                for news_item in event.get("news", []):
                    published = news_item.get("published_at", "") or news_item.get("published", "")
                    if published and len(published) >= 10:
                        date_key = published[:10]
                    else:
                        date_key = event.get("created_at", "")[:10]
                    
                    timeline_items.append({
                        "date": date_key,
                        "title": news_item["title"],
                        "link": news_item.get("url", "") or news_item.get("link", ""),
                        "source": news_item.get("source", ""),
                        "entities": event.get("entities", [])[:5],
                        "sentiment": news_item.get("sentiment", "neutral"),
                        "event_id": event["id"],
                        "event_summary": event["summary"]
                    })
        
        timeline_items.sort(key=lambda x: x["date"], reverse=True)
        
        grouped = defaultdict(list)
        for item in timeline_items:
            grouped[item["date"]].append(item)
        
        if start_date or end_date:
            filtered = {}
            for date_key, items in grouped.items():
                if start_date and date_key < start_date[:10]:
                    continue
                if end_date and date_key > end_date[:10]:
                    continue
                filtered[date_key] = items
            grouped = filtered
        
        return {
            "success": True,
            "timeline": dict(sorted(grouped.items(), reverse=True)),
            "total_items": len(timeline_items),
            "date_range": {
                "start": min(timeline_items, key=lambda x: x["date"])["date"] if timeline_items else None,
                "end": max(timeline_items, key=lambda x: x["date"])["date"] if timeline_items else None
            }
        }
    
    def _get_status_label(self, status: str) -> str:
        """获取状态中文标签"""
        labels = {
            "emerging": "萌芽期",
            "active": "发展期",
            "declining": "衰退期",
            "ended": "已结束"
        }
        return labels.get(status, status)
    
    def get_event_statistics(self) -> Dict:
        """获取事件统计信息"""
        try:
            stats = self.db.get_events_statistics()
            return {"success": True, "statistics": stats}
        except Exception as e:
            return {"success": True, "statistics": {"total_events": 0}}


# 全局实例
_tracker_instance = None


def get_event_tracker():
    """获取事件追踪器实例（单例）"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = EventTracker()
    return _tracker_instance


if __name__ == "__main__":
    # 测试
    tracker = EventTracker()
    
    test_news_1 = {
        "title": "习近平会见美国总统拜登 就中美关系进行交流",
        "content": "国家主席习近平在人民大会堂会见美国总统拜登，双方就中美关系发展深入交换意见。",
        "published": "2026-04-24 10:00:00",
        "source": "新华社"
    }
    test_news_2 = {
        "title": "中美经贸磋商取得新进展",
        "content": "中美两国在经贸领域达成多项共识，推动双边关系向前发展。",
        "published": "2026-04-24 14:00:00",
        "source": "人民日报"
    }
    
    tracker.process_news(test_news_1)
    tracker.process_news(test_news_2)
    
    events = tracker.get_event_list()
    print(f"事件总数: {events['total']}")
    for evt in events['events'][:3]:
        print(f"  - {evt['id']}: {evt['summary'][:40]}... ({evt['status_label']}, {evt['news_count']}篇)")
