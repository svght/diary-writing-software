# -*- coding: utf-8 -*-
"""
数据库连接与管理模块
提供SQLite统一存储，支持新闻、实体、事件等数据的持久化
"""

import os
import json
import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "news.db")


class Database:
    """数据库管理类 - 单例模式，线程安全"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            os.makedirs(DB_DIR, exist_ok=True)
            self._local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        conn.executescript("""
        -- 新闻表
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            url TEXT UNIQUE,
            source TEXT DEFAULT '',
            published_at TEXT DEFAULT '',
            category TEXT DEFAULT 'domestic',
            region TEXT DEFAULT '',
            sentiment TEXT DEFAULT 'neutral',
            sentiment_score REAL DEFAULT 0.0,
            hot_score INTEGER DEFAULT 0,
            quality_score INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        -- 实体表
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL DEFAULT 'unknown',
            properties TEXT DEFAULT '{}',
            first_seen TEXT DEFAULT (datetime('now', 'localtime')),
            last_seen TEXT DEFAULT (datetime('now', 'localtime')),
            mention_count INTEGER DEFAULT 1
        );

        -- 关系表
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity_id INTEGER NOT NULL,
            target_entity_id INTEGER NOT NULL,
            type TEXT DEFAULT 'co_occur',
            weight INTEGER DEFAULT 1,
            news_ids TEXT DEFAULT '[]',
            UNIQUE(source_entity_id, target_entity_id),
            FOREIGN KEY (source_entity_id) REFERENCES entities(id),
            FOREIGN KEY (target_entity_id) REFERENCES entities(id)
        );

        -- 事件表
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            summary TEXT DEFAULT '',
            status TEXT DEFAULT 'emerging',
            keywords TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            peak_count INTEGER DEFAULT 1
        );

        -- 事件-新闻关联
        CREATE TABLE IF NOT EXISTS event_news (
            event_id TEXT NOT NULL,
            news_id INTEGER NOT NULL,
            PRIMARY KEY (event_id, news_id),
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (news_id) REFERENCES news(id)
        );

        -- 事件-实体关联
        CREATE TABLE IF NOT EXISTS event_entities (
            event_id TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            PRIMARY KEY (event_id, entity_id),
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        );

        CREATE INDEX IF NOT EXISTS idx_news_category ON news(category);
        CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at);
        CREATE INDEX IF NOT EXISTS idx_news_source ON news(source);
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
        CREATE INDEX IF NOT EXISTS idx_relations_entities ON relations(source_entity_id, target_entity_id);
        CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
        """)
        conn.commit()
    
    # ==================== 新闻操作 ====================
    
    def save_news(self, news_list: List[Dict]) -> int:
        """批量保存新闻，返回新增数量"""
        conn = self._get_conn()
        saved = 0
        for item in news_list:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO news 
                    (title, content, url, source, published_at, category, region, 
                     sentiment, sentiment_score, hot_score, quality_score, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('title', ''),
                    item.get('content', '') or item.get('description', '') or item.get('title', ''),
                    item.get('link', '') or item.get('url', ''),
                    item.get('source', ''),
                    item.get('published', '') or item.get('published_at', ''),
                    item.get('_category', item.get('category', 'domestic')),
                    item.get('region', ''),
                    item.get('_sentiment', item.get('sentiment', 'neutral')),
                    float(item.get('_sentiment_score', item.get('sentiment_score', 0))),
                    int(item.get('hot_score', 0)),
                    int(item.get('quality_score', 0)),
                    item.get('description', '') or item.get('content', '')[:200] or item.get('title', '')
                ))
                if conn.total_changes > 0:
                    saved += 1
            except Exception as e:
                print(f"保存新闻失败: {e}")
        conn.commit()
        return saved
    
    def get_recent_news(self, category: str = 'all', limit: int = 30, 
                        max_hours: int = 1) -> List[Dict]:
        """获取最近N小时的新闻"""
        conn = self._get_conn()
        query = """
            SELECT * FROM news 
            WHERE datetime(created_at) >= datetime('now', ?)
        """
        params = [f'-{max_hours} hours']
        
        if category != 'all':
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY hot_score DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]
    
    def get_all_news(self, category: str = 'all', limit: int = 50) -> List[Dict]:
        """获取所有新闻"""
        conn = self._get_conn()
        if category != 'all':
            rows = conn.execute(
                "SELECT * FROM news WHERE category = ? ORDER BY hot_score DESC LIMIT ?",
                (category, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM news ORDER BY hot_score DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]
    
    def search_news_db(self, keyword: str = '', category: str = 'all', 
                       fulltext: bool = True, time_range: str = 'all',
                       source: str = '', sentiment: str = 'all',
                       max_results: int = 50) -> List[Dict]:
        """从数据库搜索新闻"""
        conn = self._get_conn()
        conditions = []
        params = []
        
        if keyword:
            kw = f'%{keyword}%'
            if fulltext:
                conditions.append("(title LIKE ? OR content LIKE ? OR source LIKE ? OR region LIKE ?)")
                params.extend([kw, kw, kw, kw])
            else:
                conditions.append("(title LIKE ? OR source LIKE ?)")
                params.extend([kw, kw])
        
        if category != 'all':
            conditions.append("category = ?")
            params.append(category)
        
        if source:
            conditions.append("source LIKE ?")
            params.append(f'%{source}%')
        
        if sentiment != 'all':
            conditions.append("sentiment = ?")
            params.append(sentiment)
        
        if time_range != 'all':
            time_map = {'24h': '-24 hours', '3d': '-3 days', '7d': '-7 days', '30d': '-30 days'}
            hours = time_map.get(time_range)
            if hours:
                conditions.append("datetime(created_at) >= datetime('now', ?)")
                params.append(hours)
        
        where = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            f"SELECT * FROM news WHERE {where} ORDER BY hot_score DESC, created_at DESC LIMIT ?",
            params + [max_results]
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]
    
    def get_news_sources(self) -> List[str]:
        """获取所有新闻来源"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT DISTINCT source FROM news WHERE source != '' ORDER BY source"
        ).fetchall()
        return [r['source'] for r in rows]
    
    def update_news_sentiment(self, news_id: int, sentiment: str, score: float):
        """更新新闻情感"""
        conn = self._get_conn()
        conn.execute(
            "UPDATE news SET sentiment = ?, sentiment_score = ? WHERE id = ?",
            (sentiment, score, news_id)
        )
        conn.commit()
    
    # ==================== 实体操作 ====================
    
    def add_entity(self, name: str, entity_type: str, properties: Dict = None) -> int:
        """添加或更新实体，返回实体ID"""
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id, mention_count FROM entities WHERE name = ?", (name,)
        ).fetchone()
        
        if existing:
            entity_id = existing['id']
            conn.execute("""
                UPDATE entities SET mention_count = mention_count + 1, 
                    last_seen = datetime('now', 'localtime'),
                    properties = CASE WHEN ? != '{}' THEN ? ELSE properties END
                WHERE id = ?
            """, (json.dumps(properties, ensure_ascii=False) if properties else '{}',
                  json.dumps(properties, ensure_ascii=False) if properties else '{}',
                  entity_id))
        else:
            cursor = conn.execute(
                "INSERT INTO entities (name, type, properties) VALUES (?, ?, ?)",
                (name, entity_type, json.dumps(properties or {}, ensure_ascii=False))
            )
            entity_id = cursor.lastrowid
        
        conn.commit()
        return entity_id
    
    def get_entity_id(self, name: str) -> Optional[int]:
        """获取实体ID"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id FROM entities WHERE name = ?", (name,)
        ).fetchone()
        return row['id'] if row else None
    
    def search_entities(self, keyword: str) -> List[Dict]:
        """搜索实体"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM entities WHERE name LIKE ? ORDER BY mention_count DESC LIMIT 50",
            (f'%{keyword}%',)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]
    
    def get_entity_detail(self, entity_id: int) -> Optional[Dict]:
        """获取实体详情"""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        if not row:
            return None
        
        # 查找关联实体
        related = conn.execute("""
            SELECT e.id, e.name, e.type, r.weight, r.type as relation_type
            FROM relations r
            JOIN entities e ON e.id = CASE 
                WHEN r.source_entity_id = ? THEN r.target_entity_id
                ELSE r.source_entity_id
            END
            WHERE r.source_entity_id = ? OR r.target_entity_id = ?
            ORDER BY r.weight DESC LIMIT 20
        """, (entity_id, entity_id, entity_id)).fetchall()
        
        result = self._row_to_dict(row)
        result['related_entities'] = [self._row_to_dict(r) for r in related]
        return result
    
    def add_relation(self, source_name: str, target_name: str, 
                     relation_type: str = "co_occur", news_id: str = ""):
        """添加实体关系"""
        source_id = self.get_entity_id(source_name)
        target_id = self.get_entity_id(target_name)
        if not source_id or not target_id or source_id == target_id:
            return
        
        conn = self._get_conn()
        
        # 标准化顺序确保唯一性
        e1_id, e2_id = min(source_id, target_id), max(source_id, target_id)
        
        existing = conn.execute(
            "SELECT id, weight, news_ids FROM relations WHERE source_entity_id = ? AND target_entity_id = ?",
            (e1_id, e2_id)
        ).fetchone()
        
        if existing:
            news_ids = json.loads(existing['news_ids'])
            if news_id and news_id not in news_ids:
                news_ids.append(news_id)
            conn.execute("""
                UPDATE relations SET weight = weight + 1, news_ids = ?
                WHERE id = ?
            """, (json.dumps(news_ids, ensure_ascii=False), existing['id']))
        else:
            conn.execute("""
                INSERT INTO relations (source_entity_id, target_entity_id, type, weight, news_ids)
                VALUES (?, ?, ?, 1, ?)
            """, (e1_id, e2_id, relation_type, 
                  json.dumps([news_id] if news_id else [], ensure_ascii=False)))
        
        conn.commit()
    
    def get_full_graph(self, min_weight: int = 1) -> Dict:
        """获取全量图谱数据"""
        conn = self._get_conn()
        
        # 获取所有实体
        nodes = conn.execute(
            "SELECT id, name, type, mention_count as count FROM entities ORDER BY mention_count DESC"
        ).fetchall()
        
        # 获取关系
        edges = conn.execute(
            "SELECT e1.name as source, e2.name as target, r.weight, r.type "
            "FROM relations r "
            "JOIN entities e1 ON e1.id = r.source_entity_id "
            "JOIN entities e2 ON e2.id = r.target_entity_id "
            "WHERE r.weight >= ? ORDER BY r.weight DESC",
            (min_weight,)
        ).fetchall()
        
        nodes_data = []
        for n in nodes:
            size = min(50, max(10, n['count'] * 3))
            nodes_data.append({
                "id": n['name'],
                "label": n['name'],
                "type": n['type'],
                "size": size,
                "count": n['count']
            })
        
        edges_data = []
        for e in edges:
            edges_data.append({
                "source": e['source'],
                "target": e['target'],
                "weight": e['weight'],
                "type": e['type']
            })
        
        # 获取统计
        stats = conn.execute("""
            SELECT 
                (SELECT COUNT(*) FROM entities) as node_count,
                (SELECT COUNT(*) FROM relations WHERE weight >= ?) as edge_count
        """, (min_weight,)).fetchone()
        
        return {
            "success": True,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": stats['node_count'],
            "edge_count": stats['edge_count'],
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def get_entity_statistics(self) -> Dict:
        """获取实体统计"""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM entities").fetchone()['c']
        
        type_dist = conn.execute(
            "SELECT type, COUNT(*) as c FROM entities GROUP BY type ORDER BY c DESC"
        ).fetchall()
        
        top = conn.execute(
            "SELECT name, type, mention_count as count FROM entities ORDER BY mention_count DESC LIMIT 10"
        ).fetchall()
        
        total_relations = conn.execute("SELECT COUNT(*) as c FROM relations").fetchone()['c']
        
        return {
            "success": True,
            "statistics": {
                "total_entities": total,
                "type_distribution": {r['type']: r['c'] for r in type_dist},
                "top_entities": [self._row_to_dict(r) for r in top],
                "total_relations": total_relations
            }
        }
    
    # ==================== 事件操作 ====================
    
    def save_event(self, event_id: str, summary: str, status: str,
                   keywords: List[str], entities: List[str]):
        """保存事件"""
        conn = self._get_conn()
        existing = conn.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone()
        
        if existing:
            conn.execute("""
                UPDATE events SET summary = ?, status = ?, keywords = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            """, (summary, status, json.dumps(keywords, ensure_ascii=False), event_id))
        else:
            conn.execute("""
                INSERT INTO events (id, summary, status, keywords)
                VALUES (?, ?, ?, ?)
            """, (event_id, summary, status, json.dumps(keywords, ensure_ascii=False)))
        
        # 关联实体
        for entity_name in entities:
            entity_id = self.get_entity_id(entity_name)
            if entity_id:
                conn.execute(
                    "INSERT OR IGNORE INTO event_entities (event_id, entity_id) VALUES (?, ?)",
                    (event_id, entity_id)
                )
        
        conn.commit()
    
    def link_news_to_event(self, event_id: str, news_id: int):
        """关联新闻到事件"""
        conn = self._get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO event_news (event_id, news_id) VALUES (?, ?)",
            (event_id, news_id)
        )
        conn.commit()
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """获取事件"""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            return None
        event = self._row_to_dict(row)
        event['keywords'] = json.loads(event.get('keywords', '[]'))
        
        # 获取关联新闻
        news_rows = conn.execute("""
            SELECT n.* FROM news n
            JOIN event_news en ON en.news_id = n.id
            WHERE en.event_id = ?
            ORDER BY n.created_at DESC
        """, (event_id,)).fetchall()
        event['news'] = [self._row_to_dict(n) for n in news_rows]
        event['news_count'] = len(news_rows)
        
        # 获取关联实体
        entity_rows = conn.execute("""
            SELECT e.name FROM entities e
            JOIN event_entities ee ON ee.entity_id = e.id
            WHERE ee.event_id = ?
        """, (event_id,)).fetchall()
        event['entities'] = [r['name'] for r in entity_rows]
        
        return event
    
    def get_events_list(self, status: str = 'all', limit: int = 20) -> List[Dict]:
        """获取事件列表"""
        conn = self._get_conn()
        if status != 'all':
            rows = conn.execute(
                "SELECT * FROM events WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        
        result = []
        for row in rows:
            event = self._row_to_dict(row)
            event['keywords'] = json.loads(event.get('keywords', '[]'))
            # 获取新闻数量
            cnt = conn.execute(
                "SELECT COUNT(*) as c FROM event_news WHERE event_id = ?",
                (event['id'],)
            ).fetchone()['c']
            event['news_count'] = cnt
            
            # 获取实体列表
            entities = conn.execute("""
                SELECT e.name FROM entities e
                JOIN event_entities ee ON ee.entity_id = e.id
                WHERE ee.event_id = ?
            """, (event['id'],)).fetchall()
            event['entities'] = [r['name'] for r in entities]
            
            result.append(event)
        
        return result
    
    def get_event_news_ids(self, event_id: str) -> List[int]:
        """获取事件关联的新闻ID列表"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT news_id FROM event_news WHERE event_id = ?", (event_id,)
        ).fetchall()
        return [r['news_id'] for r in rows]
    
    def get_entity_news_ids(self, entity_name: str) -> List[int]:
        """获取包含某实体的新闻ID列表"""
        conn = self._get_conn()
        entity_id = self.get_entity_id(entity_name)
        if not entity_id:
            return []
        
        # 通过关系表找到包含该实体的新闻
        rows = conn.execute("""
            SELECT DISTINCT json_each.value as news_id
            FROM relations, json_each(relations.news_ids)
            WHERE (source_entity_id = ? OR target_entity_id = ?)
              AND json_each.value != ''
        """, (entity_id, entity_id)).fetchall()
        
        news_ids = []
        for r in rows:
            val = r['news_id']
            # news_ids 存储的是 url/title 字符串，需要转为 id
            news_row = conn.execute(
                "SELECT id FROM news WHERE url = ? OR title = ?",
                (val, val)
            ).fetchone()
            if news_row:
                news_ids.append(news_row['id'])
        
        return news_ids
    
    def get_event_id_counter(self) -> int:
        """获取当前事件ID计数器"""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()
        return row['c']
    
    def update_event_status(self, event_id: str, status: str, peak_count: int = None):
        """更新事件状态"""
        conn = self._get_conn()
        if peak_count:
            conn.execute(
                "UPDATE events SET status = ?, updated_at = datetime('now', 'localtime'), peak_count = ? WHERE id = ?",
                (status, peak_count, event_id)
            )
        else:
            conn.execute(
                "UPDATE events SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (status, event_id)
            )
        conn.commit()
    
    def get_events_statistics(self) -> Dict:
        """获取事件统计"""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()['c']
        
        status_dist = conn.execute(
            "SELECT status, COUNT(*) as c FROM events GROUP BY status"
        ).fetchall()
        
        total_news = conn.execute("SELECT COUNT(*) as c FROM event_news").fetchone()['c']
        
        return {
            "total_events": total,
            "status_distribution": {r['status']: r['c'] for r in status_dist},
            "total_news_in_events": total_news,
            "avg_news_per_event": round(total_news / max(total, 1), 1)
        }
    
    # ==================== 工具方法 ====================
    
    def _row_to_dict(self, row) -> Dict:
        """将sqlite3.Row转换为字典"""
        if isinstance(row, sqlite3.Row):
            return dict(row)
        return dict(row)
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# 全局单例
_db_instance = None


def get_database():
    """获取数据库实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
