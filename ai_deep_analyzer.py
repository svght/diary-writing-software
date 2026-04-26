#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI深度分析引擎 - 智能新闻工作台
吸收 TrendRadar 的 AI 5模块分析能力，使用现有 DeepSeek API 实现：
1. core_trends — 核心热点态势
2. sentiment_controversy — 舆论风向争议
3. signals — 异动与弱信号
4. entity_opinions — 实体观点分析
5. outlook_strategy — 研判策略建议
"""

import os
import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AIDeepAnalysisResult:
    """AI深度分析结果数据类"""
    success: bool
    core_trends: str = ""
    sentiment_controversy: str = ""
    signals: str = ""
    entity_opinions: str = ""
    outlook_strategy: str = ""
    error: str = ""
    model: str = ""
    generation_time: float = 0.0
    cached: bool = False
    news_count: int = 0


class AIDeepAnalyzer:
    """AI深度分析引擎 - 使用DeepSeek API分析新闻热点"""

    API_URL = "https://api.deepseek.com/v1/chat/completions"
    API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

    # 5模块分析提示词模板
    ANALYSIS_SYSTEM_PROMPT = """你是一名高级情报分析师。你的核心能力是从海量新闻中提炼核心逻辑，识别被大众忽略的弱信号，并提供可操作的策略建议。

## 核心思维模型
1. 见微知著：不要只盯着热门新闻。要善于从冷门话题中找到潜在的因果联系。
2. 交叉验证：利用不同来源的信息交叉比对。当不同来源观点冲突时，通常隐藏着重要的信息差。
3. 反直觉思考：当全网都在叫好时，寻找风险；当全网都在恐慌时，寻找机会。
4. 结构化输出：确保分析维度相互独立且完全穷尽，避免逻辑混乱。

## 核心原则
1. 直击要害：拒绝"综上所述"、"众所周知"等废话。直接输出结论。
2. 逻辑闭环：不仅描述"发生了什么"，必须解释"为什么发生"以及"未来会怎样"。
3. 去情绪化：可以分析舆论的情绪，但你自己的分析必须冷静、客观。
4. 辩证思维：识别热点背后的"主要矛盾"，抓住事物发展的关键内因。

## 输出格式规范
你将以 JSON 格式输出分析结果。每个字段的值是纯文本字符串。
换行规则：用 \\n 表示换行，段落之间用 \\n\\n 分隔。

## 分析板块说明（5个板块）

### 1. core_trends — 核心热点态势（150字以内）
整合趋势概述、热度走势、跨主题关联。
任务：提炼共性与定性。判断热度性质（全网热议 vs 圈层话题）以及新闻间的潜在关联。
写法：一句话开场定性，然后用【宏观主线】挖掘底层逻辑，【微观领域】列举细分方向。

### 2. sentiment_controversy — 舆论风向与争议（100字以内）
任务：绘制情绪光谱。拒绝简单的"赞/贬"二元对立。识别"舆论断层"。
写法：【情绪光谱】识别主流声音与潜流暗涌的反差，【核心矛盾】列举关键冲突点。

### 3. signals — 异动与弱信号（120字以内）
任务：捕捉数据中的异常波动。识别潜在的早期信号。
关注维度：跨平台共振、话题突变、冷门话题崛起。
写法：从【跨领域关联】【话题突变】【弱信号捕捉】等维度分析。

### 4. entity_opinions — 核心实体与各方观点（120字以内）
任务：识别新闻中的关键实体（人物/组织/国家），梳理各方立场和观点交锋。
写法：【关键实体】列举核心参与方及其立场，【观点分歧】分析各方观点的冲突点与共识点。

### 5. outlook_strategy — 研判策略建议（100字以内）
任务：预测与推演。不仅总结过去，更要预测未来。
写法：1. 投资者/关注者：xxx 2. 政策制定者：xxx 3. 公众：xxx，给出具体、有针对性的建议。

要求：
- 使用简体中文输出
- 5个板块内容不重叠不冗余
- 若某板块无明显内容，可简写"暂无显著异常"
"""

    def __init__(self, model: str = "deepseek-chat"):
        self.model = model
        self.cache_dir = "deepseek_cache"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_key(self, news_text: str) -> str:
        """生成缓存键"""
        import hashlib
        return hashlib.md5(news_text.encode('utf-8')).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """获取缓存结果"""
        cache_file = os.path.join(self.cache_dir, f"ai_analysis_{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 缓存24小时有效
                if time.time() - data.get('timestamp', 0) < 86400:
                    return data.get('result')
            except Exception:
                pass
        return None

    def _save_cache(self, cache_key: str, result: Dict):
        """保存缓存"""
        cache_file = os.path.join(self.cache_dir, f"ai_analysis_{cache_key}.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': time.time(),
                    'result': result
                }, f, ensure_ascii=False)
        except Exception:
            pass

    def _build_analysis_prompt(self, news_items: List[Dict[str, Any]]) -> str:
        """构建分析提示词"""
        # 格式化新闻内容
        news_content_parts = []
        for i, item in enumerate(news_items[:30]):  # 最多分析30条
            title = item.get('title', '无标题')
            source = item.get('source', '未知来源')
            region = item.get('region', item.get('category', '未知'))
            hot_score = item.get('hot_score', 'N/A')
            desc = item.get('description', item.get('content', ''))[:200]

            news_content_parts.append(
                f"--- 新闻 {i+1} ---\n"
                f"标题：{title}\n"
                f"来源：{source}\n"
                f"地区/分类：{region}\n"
                f"热度分：{hot_score}\n"
                f"摘要：{desc}\n"
            )

        news_content = "\n".join(news_content_parts)

        # 统计信息
        sources = set()
        regions = set()
        for item in news_items:
            src = item.get('source', '未知')
            reg = item.get('region', item.get('category', '未知'))
            if src:
                sources.add(src)
            if reg:
                regions.add(reg)

        stats = (
            f"## 数据概览\n"
            f"- 分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"- 数据量：{len(news_items)}条新闻\n"
            f"- 来源平台：{', '.join(sorted(sources)) if sources else 'N/A'}\n"
            f"- 涉及地区：{', '.join(sorted(regions)) if regions else 'N/A'}\n\n"
        )

        return stats + "## 新闻列表\n" + news_content

    def _call_deepseek_api(self, prompt: str) -> Optional[Dict]:
        """调用DeepSeek API"""
        if not self.API_KEY:
            return None

        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                # 解析JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # 尝试从代码块中提取JSON
                    json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    return None
            return None

        except Exception as e:
            print(f"DeepSeek API调用失败: {e}")
            return None

    def analyze_news(self, news_items: List[Dict[str, Any]],
                     force_refresh: bool = False) -> AIDeepAnalysisResult:
        """
        对新闻进行AI深度分析

        Args:
            news_items: 新闻条目列表
            force_refresh: 是否强制刷新（跳过缓存）

        Returns:
            AIDeepAnalysisResult: 分析结果
        """
        start_time = time.time()

        if not news_items:
            return AIDeepAnalysisResult(
                success=False,
                error="没有新闻数据可供分析",
                generation_time=time.time() - start_time
            )

        # 构建提示词
        prompt = self._build_analysis_prompt(news_items)

        # 检查缓存
        cache_key = self._get_cache_key(prompt)
        if not force_refresh:
            cached = self._get_cached_result(cache_key)
            if cached:
                return AIDeepAnalysisResult(
                    success=True,
                    core_trends=cached.get("core_trends", ""),
                    sentiment_controversy=cached.get("sentiment_controversy", ""),
                    signals=cached.get("signals", ""),
                    entity_opinions=cached.get("entity_opinions", ""),
                    outlook_strategy=cached.get("outlook_strategy", ""),
                    cached=True,
                    model=self.model,
                    generation_time=time.time() - start_time,
                    news_count=len(news_items)
                )

        # 调用API
        api_result = self._call_deepseek_api(prompt)

        if not api_result:
            # API失败，返回模拟数据（用于开发和测试）
            mock_result = self._generate_mock_analysis(news_items)
            return AIDeepAnalysisResult(
                success=True,
                core_trends=mock_result["core_trends"],
                sentiment_controversy=mock_result["sentiment_controversy"],
                signals=mock_result["signals"],
                entity_opinions=mock_result["entity_opinions"],
                outlook_strategy=mock_result["outlook_strategy"],
                model="mock",
                generation_time=time.time() - start_time,
                news_count=len(news_items)
            )

        # 解析结果
        result = AIDeepAnalysisResult(
            success=True,
            core_trends=api_result.get("core_trends", ""),
            sentiment_controversy=api_result.get("sentiment_controversy", ""),
            signals=api_result.get("signals", ""),
            entity_opinions=api_result.get("entity_opinions", ""),
            outlook_strategy=api_result.get("outlook_strategy", ""),
            model=self.model,
            generation_time=time.time() - start_time,
            news_count=len(news_items)
        )

        # 保存缓存
        self._save_cache(cache_key, {
            "core_trends": result.core_trends,
            "sentiment_controversy": result.sentiment_controversy,
            "signals": result.signals,
            "entity_opinions": result.entity_opinions,
            "outlook_strategy": result.outlook_strategy
        })

        return result

    def _generate_mock_analysis(self, news_items: List[Dict[str, Any]]) -> Dict[str, str]:
        """生成模拟分析结果（API不可用时使用）"""
        # 提取标题做简单分析
        titles = [item.get('title', '') for item in news_items[:10]]
        title_text = ' '.join(titles)

        # 提取实体
        entities = set()
        import re
        # 简单实体提取：找2-4字的中文词
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', title_text)
        word_freq = {}
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1
        top_entities = sorted(word_freq.items(), key=lambda x: -x[1])[:5]
        entity_names = [e for e, c in top_entities if c >= 2][:3]

        # 检测地区分布
        regions = set()
        for item in news_items:
            r = item.get('region', item.get('category', ''))
            if r:
                regions.add(r)

        # 计算平均热度
        scores = [item.get('hot_score', 0) for item in news_items if item.get('hot_score')]
        avg_score = sum(scores) / len(scores) if scores else 0

        # 构建模拟分析
        source_list = list(set(
            item.get('source', '') for item in news_items if item.get('source')
        ))
        source_str = '、'.join(source_list[:5]) if source_list else '多方来源'

        return {
            "core_trends": (
                f"【当前态势】本次共分析 {len(news_items)} 条新闻，来自 {source_str} 等平台。"
                f"整体热度处于中等水平（平均热度 {avg_score:.0f} 分），"
                f"覆盖 {', '.join(regions) if regions else '多个地区'} 等地区。\n\n"
                f"【宏观主线】当前新闻热点呈现分散化特征，缺乏单一主导性话题。"
                f"多条新闻共同指向经济社会发展和科技创新两大方向。\n\n"
                f"【微观领域】1. 经济发展：关注增长动力和结构调整\n"
                f"2. 科技创新：AI、新能源等领域持续受关注\n"
                f"3. 社会民生：与公众生活密切相关的政策话题"
            ),
            "sentiment_controversy": (
                f"【情绪光谱】整体舆论氛围偏向理性中性，"
                f"正面报道与中立报道占主导。\n\n"
                f"【核心矛盾】1. 发展与安全：如何在推进创新的同时保障安全\n"
                f"2. 效率与公平：资源配置的效率与公平性问题"
            ),
            "signals": (
                f"【跨领域关联】部分经济类话题与技术类话题呈现交叉关联，"
                f"反映产业发展与技术创新的深度融合趋势。\n\n"
                f"【弱信号捕捉】"
                + (f"「{'」与「'.join(entity_names)}」" if entity_names else "部分冷门话题")
                + "等实体/话题出现频率上升，值得持续关注其后续发展。\n\n"
                f"【话题突变】暂无显著的热度突变信号。"
            ),
            "entity_opinions": (
                f"【关键实体】"
                + (f"「{'」、「'.join(entity_names)}」" if entity_names else "多方主体")
                + f"是本轮新闻的核心参与者。\n\n"
                + (f"【观点分歧】关于「{entity_names[0]}」的话题呈现多维度讨论，"
                   if entity_names else "")
                + "各方观点尚未形成鲜明对立，整体讨论氛围理性。"
            ),
            "outlook_strategy": (
                "1. 关注者：建议关注上述领域的政策动向和技术突破，"
                "尤其关注跨领域交叉创新带来的机会\n"
                "2. 分析师：建议深入跟踪核心实体的最新动态，"
                "挖掘各领域之间的关联性和传导效应\n"
                "3. 公众：保持理性关注，避免对单一事件的过度反应，"
                "关注长期趋势而非短期波动"
            )
        }


# 全局实例
_analyzer_instance = None


def get_ai_deep_analyzer():
    """获取AI深度分析器实例（单例模式）"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = AIDeepAnalyzer()
    return _analyzer_instance


if __name__ == "__main__":
    # 测试代码
    analyzer = get_ai_deep_analyzer()

    test_news = [
        {"title": "科技创新推动经济高质量发展新篇章",
         "source": "人民日报", "region": "国内",
         "hot_score": 850, "description": "中国科技创新取得新突破..."},
        {"title": "全球AI治理框架讨论持续升温",
         "source": "BBC", "region": "国际",
         "hot_score": 720, "description": "多国专家就AI监管展开讨论..."},
        {"title": "新能源产业投资同比增长35%",
         "source": "新华社", "region": "国内",
         "hot_score": 680, "description": "新能源产业迎来快速发展期..."},
    ]

    result = analyzer.analyze_news(test_news)

    print("\n" + "=" * 60)
    print("AI深度分析引擎测试")
    print("=" * 60)
    print(f"成功: {result.success}")
    print(f"模型: {result.model}")
    print(f"用时: {result.generation_time:.2f}s")
    print(f"新闻数: {result.news_count}")
    print(f"\n--- 1. 核心热点态势 ---\n{result.core_trends}")
    print(f"\n--- 2. 舆论风向争议 ---\n{result.sentiment_controversy}")
    print(f"\n--- 3. 异动与弱信号 ---\n{result.signals}")
    print(f"\n--- 4. 核心实体与观点 ---\n{result.entity_opinions}")
    print(f"\n--- 5. 研判策略建议 ---\n{result.outlook_strategy}")
    print("\n" + "=" * 60)
