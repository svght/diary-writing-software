#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体深度挖掘模块
使用SQLite数据库统一存储
"""

import json
import os
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
from database import get_database


class EntityMiner:
    """实体挖掘器 - 对实体进行深度分析（数据库版）"""
    
    def __init__(self):
        self.db = get_database()
    
    def build_profile(self, entity_name: str, entity_type: str,
                      related_entities: List[Dict],
                      timeline_data: Dict) -> Dict:
        """构建或更新实体画像"""
        entity_id = self.db.get_entity_id(entity_name)
        if not entity_id:
            entity_id = self.db.add_entity(entity_name, entity_type)
        
        # 获取已有数据
        detail = self.db.get_entity_detail(entity_id)
        
        profile = {
            "name": entity_name,
            "type": entity_type,
            "first_seen": detail.get("first_seen", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_news": 0,
            "total_relations": len(detail.get("related_entities", [])),
            "related_entities": {},
            "timeline": {},
            "sentiment_distribution": {}
        }
        
        # 更新关联实体
        for rel in related_entities:
            rel_name = rel.get("entity", "")
            rel_type = rel.get("type", "unknown")
            weight = rel.get("weight", 1)
            if rel_name:
                if rel_name in profile["related_entities"]:
                    profile["related_entities"][rel_name]["weight"] += weight
                else:
                    profile["related_entities"][rel_name] = {
                        "type": rel_type,
                        "weight": weight,
                        "first_seen": profile["last_updated"]
                    }
        
        # 更新时间线
        if timeline_data.get("timeline"):
            for date_key, items in timeline_data["timeline"].items():
                if date_key not in profile["timeline"]:
                    profile["timeline"][date_key] = []
                for item in items:
                    title = item.get("title", "")
                    existing_titles = {n["title"] for n in profile["timeline"][date_key]}
                    if title not in existing_titles:
                        profile["timeline"][date_key].append({
                            "title": title,
                            "link": item.get("link", ""),
                            "source": item.get("source", ""),
                            "sentiment": item.get("sentiment", "neutral"),
                            "event_id": item.get("event_id", ""),
                            "event_summary": item.get("event_summary", "")
                        })
        
        total_news = sum(len(items) for items in profile["timeline"].values())
        profile["total_news"] = total_news
        
        sentiments = []
        for items in profile["timeline"].values():
            for item in items:
                sentiments.append(item.get("sentiment", "neutral"))
        
        sentiment_counts = defaultdict(int)
        for s in sentiments:
            sentiment_counts[s] += 1
        if sentiments:
            profile["sentiment_distribution"] = dict(sentiment_counts)
        
        # 保存到数据库的 properties 字段
        self.db.add_entity(entity_name, entity_type, {
            "type": entity_type,
            "last_updated": profile["last_updated"],
            "total_news": total_news,
            "total_relations": profile["total_relations"]
        })
        
        return profile
    
    def get_profile(self, entity_name: str,
                    graph_data: Dict = None,
                    timeline_data: Dict = None) -> Dict:
        """获取实体画像"""
        entity_id = self.db.get_entity_id(entity_name)
        if not entity_id:
            return {"success": False, "error": "实体不存在，请先分析数据"}
        
        detail = self.db.get_entity_detail(entity_id)
        if not detail:
            return {"success": False, "error": "实体不存在"}
        
        # 如果有图谱和时间线数据，先构建/更新
        if graph_data or timeline_data:
            entity_info = graph_data.get("entity") if graph_data else None
            related = graph_data.get("related_entities", []) if graph_data else []
            entity_type = entity_info.get("type", "unknown") if entity_info else "unknown"
            
            profile = self.build_profile(
                entity_name=entity_name,
                entity_type=entity_type,
                related_entities=related,
                timeline_data=timeline_data or {"timeline": {}}
            )
            return {"success": True, "profile": profile}
        
        # 返回基本信息
        profile = {
            "name": detail.get("name", entity_name),
            "type": detail.get("type", "unknown"),
            "first_seen": detail.get("first_seen", ""),
            "last_updated": detail.get("last_seen", ""),
            "total_news": 0,
            "total_relations": len(detail.get("related_entities", [])),
            "related_entities": {},
            "timeline": {},
            "sentiment_distribution": {}
        }
        
        # 关联实体
        for rel in detail.get("related_entities", []):
            rel_name = rel.get("name", "")
            if rel_name:
                profile["related_entities"][rel_name] = {
                    "type": rel.get("type", "unknown"),
                    "weight": rel.get("weight", 1),
                    "first_seen": ""
                }
        
        return {"success": True, "profile": profile}
    
    def get_entity_network(self, entity_name: str, max_nodes: int = 20) -> Dict:
        """获取实体关联网络"""
        entity_id = self.db.get_entity_id(entity_name)
        if not entity_id:
            return {"success": False, "error": "实体不存在"}
        
        detail = self.db.get_entity_detail(entity_id)
        if not detail:
            return {"success": False, "error": "实体不存在"}
        
        related = detail.get("related_entities", [])
        entity_type = detail.get("type", "unknown")
        
        nodes = [
            {
                "id": entity_name,
                "label": entity_name,
                "type": entity_type,
                "size": 30,
                "is_center": True
            }
        ]
        
        edges = []
        
        sorted_related = sorted(related, key=lambda x: x.get("weight", 0), reverse=True)
        for rel in sorted_related[:max_nodes - 1]:
            rel_name = rel.get("name", "")
            weight = rel.get("weight", 1)
            size = min(25, max(8, weight * 2))
            nodes.append({
                "id": rel_name,
                "label": rel_name,
                "type": rel.get("type", "unknown"),
                "size": size,
                "is_center": False
            })
            edges.append({
                "source": entity_name,
                "target": rel_name,
                "weight": weight
            })
        
        return {
            "success": True,
            "entity_name": entity_name,
            "network": {
                "nodes": nodes,
                "edges": edges
            },
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    
    def get_entity_sentiment_trend(self, entity_name: str) -> Dict:
        """获取实体情感趋势"""
        profile = self.get_profile(entity_name)
        if not profile.get("success"):
            return profile
        
        profile_data = profile["profile"]
        timeline = profile_data.get("timeline", {})
        
        date_sentiments = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0})
        for date_key, items in timeline.items():
            for item in items:
                sentiment = item.get("sentiment", "neutral")
                date_sentiments[date_key][sentiment] += 1
                date_sentiments[date_key]["total"] += 1
        
        sorted_dates = sorted(date_sentiments.keys())
        
        dates = []
        positive_ratios = []
        negative_ratios = []
        neutral_ratios = []
        
        for date_key in sorted_dates:
            stats = date_sentiments[date_key]
            total = stats["total"]
            if total > 0:
                dates.append(date_key)
                positive_ratios.append(round(stats["positive"] / total * 100, 1))
                negative_ratios.append(round(stats["negative"] / total * 100, 1))
                neutral_ratios.append(round(stats["neutral"] / total * 100, 1))
        
        sentiment_dist = profile_data.get("sentiment_distribution", {})
        
        return {
            "success": True,
            "entity_name": entity_name,
            "dates": dates,
            "positive_ratios": positive_ratios,
            "negative_ratios": negative_ratios,
            "neutral_ratios": neutral_ratios,
            "sentiment_distribution": sentiment_dist,
            "total_analyzed": sum(sentiment_dist.values()) if sentiment_dist else 0
        }
    
    def get_entity_news(self, entity_name: str, limit: int = 20) -> Dict:
        """获取实体相关新闻"""
        profile = self.get_profile(entity_name)
        if not profile.get("success"):
            return profile
        
        profile_data = profile["profile"]
        timeline = profile_data.get("timeline", {})
        
        all_news = []
        for date_key, items in timeline.items():
            for item in items:
                all_news.append({
                    "date": date_key,
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "source": item.get("source", ""),
                    "sentiment": item.get("sentiment", "neutral"),
                    "event_id": item.get("event_id", ""),
                    "event_summary": item.get("event_summary", "")
                })
        
        all_news.sort(key=lambda x: x["date"], reverse=True)
        
        return {
            "success": True,
            "entity_name": entity_name,
            "news": all_news[:limit],
            "total": len(all_news),
            "returned": min(limit, len(all_news))
        }
    
    def get_entity_timeline_data(self, entity_name: str) -> Dict:
        """获取实体时间线数据（用于前端时间线视图）"""
        profile = self.get_profile(entity_name)
        if not profile.get("success"):
            return profile
        
        profile_data = profile["profile"]
        timeline = profile_data.get("timeline", {})
        
        grouped_timeline = []
        for date_key in sorted(timeline.keys(), reverse=True):
            items = timeline[date_key]
            grouped_timeline.append({
                "date": date_key,
                "items": items,
                "count": len(items)
            })
        
        all_dates = sorted(timeline.keys())
        
        return {
            "success": True,
            "entity_name": entity_name,
            "timeline": grouped_timeline,
            "total_items": sum(len(items) for items in timeline.values()),
            "date_range": {
                "start": all_dates[0] if all_dates else None,
                "end": all_dates[-1] if all_dates else None
            }
        }
    
    def search_entity_profiles(self, keyword: str) -> List[Dict]:
        """搜索实体画像"""
        return self.db.search_entities(keyword)
    
    def get_entity_statistics(self) -> Dict:
        """获取实体深度分析统计"""
        return self.db.get_entity_statistics()


# 全局实例
_miner_instance = None


def get_entity_miner():
    """获取实体挖掘器实例（单例）"""
    global _miner_instance
    if _miner_instance is None:
        _miner_instance = EntityMiner()
    return _miner_instance


if __name__ == "__main__":
    miner = EntityMiner()
    result = miner.search_entity_profiles("习")
    print(f"搜索 '习' 找到 {len(result)} 个画像")
    stats = miner.get_entity_statistics()
    print(f"画像统计: {stats}")
