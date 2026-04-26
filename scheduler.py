#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能调度系统 - 智能新闻工作台
整合定时任务调度、日报生成、widget dashboard 功能
"""
import os, json, threading, time, logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    name: str
    interval_minutes: int
    last_run: float = 0
    enabled: bool = True
    callback: Optional[Callable] = None


class ReportGenerator:
    """日报/简报生成器"""
    def generate_daily_brief(self, news_items: List[Dict], sentiment: Dict = None) -> Dict:
        hot = sorted(news_items, key=lambda x: x.get('hot_score', 0), reverse=True)[:10]
        from collections import Counter
        sources = Counter(n.get('source','') for n in news_items if n.get('source'))
        regions = Counter(n.get('region', n.get('category','')) for n in news_items)
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_news": len(news_items),
            "top_news": [{"title":n.get('title',''),"source":n.get('source',''),"score":n.get('hot_score',0)} for n in hot],
            "source_distribution": dict(sources.most_common(10)),
            "region_distribution": dict(regions.most_common(10)),
            "sentiment": sentiment or {},
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def render_html(self, brief: Dict) -> str:
        top_items = "".join(f'<li>{n["title"]} <small>({n["source"]}, {n["score"]})</small></li>' for n in brief["top_news"])
        src_items = "".join(f'<li>{k}: {v}篇</li>' for k,v in brief["source_distribution"].items())
        return f"""<html><head><meta charset="utf-8"><title>每日简报 {brief["date"]}</title>
<style>body{{font-family:'Microsoft YaHei',sans-serif;max-width:800px;margin:auto;padding:20px;}}
h1{{color:#1e40af;}}h2{{color:#374151;border-bottom:2px solid #e5e7eb;padding-bottom:8px;}}
ul{{line-height:1.8;}}.meta{{color:#6b7280;font-size:12px;}}</style></head><body>
<h1>📰 每日新闻简报</h1><p class="meta">生成时间: {brief["generated_at"]} | 共 {brief["total_news"]} 条</p>
<h2>🏆 热点 TOP 10</h2><ul>{top_items}</ul>
<h2>📡 来源分布</h2><ul>{src_items}</ul>
<h2>🌍 地区分布</h2><ul>{"".join(f'<li>{k}: {v}篇</li>' for k,v in brief["region_distribution"].items())}</ul>
<h2>💬 情感概览</h2><pre>{json.dumps(brief["sentiment"], ensure_ascii=False, indent=2)}</pre>
</body></html>"""

    def save(self, brief: Dict, html: str) -> str:
        out_dir = "daily_briefs"
        os.makedirs(out_dir, exist_ok=True)
        fname = f"{out_dir}/brief_{brief['date']}.html"
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(html)
        return fname


class WidgetDashboard:
    """Widget Dashboard配置管理 - 吸收Glance的widget概念"""
    DEFAULT_WIDGETS = {
        "weather": {"enabled": True, "order": 1},
        "trend": {"enabled": True, "order": 2},
        "ai_analysis": {"enabled": True, "order": 3},
        "scoring": {"enabled": True, "order": 4},
        "interest_filter": {"enabled": True, "order": 5},
        "opinion_monitor": {"enabled": True, "order": 6},
        "entity_graph": {"enabled": True, "order": 7},
        "event_tracker": {"enabled": True, "order": 8},
        "entity_miner": {"enabled": True, "order": 9},
    }

    def __init__(self):
        self.config_file = "config/dashboard.json"
        self._widgets = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return dict(self.DEFAULT_WIDGETS)

    def _save(self):
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._widgets, f, ensure_ascii=False, indent=2)

    def get_widgets(self) -> Dict:
        return self._widgets

    def toggle_widget(self, name: str, enabled: bool) -> bool:
        if name in self._widgets:
            self._widgets[name]["enabled"] = enabled
            self._save()
            return True
        return False

    def reorder(self, name: str, new_order: int) -> bool:
        if name in self._widgets:
            self._widgets[name]["order"] = new_order
            self._save()
            return True
        return False


class Scheduler:
    """调度管理器"""
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self._thread = None
        self._running = False

    def add_task(self, task: ScheduledTask):
        self.tasks[task.name] = task

    def _run_loop(self):
        while self._running:
            now = time.time()
            for task in self.tasks.values():
                if task.enabled and task.callback and (now - task.last_run) >= task.interval_minutes * 60:
                    try:
                        logger.info(f"执行定时任务: {task.name}")
                        task.callback()
                        task.last_run = now
                    except Exception as e:
                        logger.error(f"任务[{task.name}]失败: {e}")
            time.sleep(30)

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("调度器已启动")

    def stop(self):
        self._running = False


# Globals
_scheduler = None
_report_gen = None
_dashboard = None

def get_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler

def get_report_generator():
    global _report_gen
    if _report_gen is None:
        _report_gen = ReportGenerator()
    return _report_gen

def get_dashboard():
    global _dashboard
    if _dashboard is None:
        _dashboard = WidgetDashboard()
    return _dashboard
