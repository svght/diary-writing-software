#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能新闻工作台 - 浏览器版
使用 Flask 提供本地浏览器界面，集新闻采集、多类型评论生成、多风格改写于一体。
"""

import os
import json
import webbrowser
from datetime import datetime

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from weather_service import WeatherService
from location_service import LocationService, CHINESE_CITIES
from news_service import NewsService
from news_analyzer import get_analyzer, extract_entities_from_news
from news_summarizer import get_summarizer, generate_summary_for_news
from sentiment_analyzer import get_sentiment_analyzer, analyze_sentiment_from_news
from trend_analyzer import get_trend_analyzer, update_trend_with_news
from region_analyzer import get_region_analyzer, update_region_with_news
from database import get_database
from deepseek_comment_generator import get_deepseek_generator
from word_cloud_service import get_word_cloud_service
from entity_graph import get_entity_graph, get_entity_extractor, process_news_for_graph
from event_tracker import get_event_tracker
from entity_miner import get_entity_miner
from ai_deep_analyzer import get_ai_deep_analyzer
from news_scorer import get_news_scorer
from trend_analyzer import get_trend_analyzer, calculate_news_weight
from notification_manager import get_notification_manager
from ai_filter import get_ai_filter
from public_opinion_monitor import get_opinion_monitor
from scheduler import get_scheduler, get_report_generator, get_dashboard, ScheduledTask


app = Flask(__name__, template_folder="templates", static_folder="static")
weather_service = WeatherService()
location_service = LocationService()
news_service = NewsService()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


@app.route('/')
def index():
    default_city = location_service.get_city_by_ip() or '北京'
    return render_template(
        'index.html',
        default_city=default_city,
        cities=CHINESE_CITIES,
    )


@app.route('/api/weather')
def api_weather():
    city = request.args.get('city', '').strip() or '北京'
    weather = weather_service.get_current_weather(city)
    if not weather:
        return jsonify(success=False, error='无法获取天气信息，请检查网络'), 503
    return jsonify(success=True, weather=weather)


@app.route('/api/news')
def api_news():
    news = news_service.get_hot_news()

    # 更新热度趋势数据
    try:
        update_trend_with_news(news)
    except Exception as e:
        print(f"更新趋势数据失败: {e}")

    # 更新地区分布数据
    try:
        all_news = []
        if 'domestic' in news:
            all_news.extend(news['domestic'])
        if 'international' in news:
            all_news.extend(news['international'])

        if all_news:
            update_region_with_news(all_news)
    except Exception as e:
        print(f"更新地区数据失败: {e}")

    return jsonify(success=True, **news)


@app.route('/api/news/analyze/entities', methods=['POST'])
def api_analyze_entities():
    """分析新闻实体（人物+国家）"""
    try:
        data = request.json or {}
        text = data.get('text', '')
        title = data.get('title', '')
        news_id = data.get('news_id')

        if not text and news_id:
            news_data = news_service.get_hot_news()
            for category in ['domestic', 'international']:
                if category in news_data:
                    for item in news_data[category]:
                        if str(item.get('link', '')).find(str(news_id)) != -1 or \
                           str(item.get('title', '')).find(str(news_id)) != -1:
                            title = item.get('title', '')
                            content = item.get('content', '') or item.get('description', '') or title
                            text = content
                            break

        if not text and title:
            text = title

        if not text:
            return jsonify(success=False, error='请提供新闻文本、标题或新闻ID'), 400

        analyzer = get_analyzer()
        result = analyzer.extract_entities(text, title)

        return jsonify({
            "success": True,
            "entities": result,
            "text_preview": text[:100] + "..." if len(text) > 100 else text
        })

    except Exception as e:
        return jsonify(success=False, error=f'分析失败: {str(e)}'), 500


@app.route('/api/news/analyze/summary', methods=['POST'])
def api_analyze_summary():
    """生成新闻摘要"""
    try:
        data = request.json or {}
        text = data.get('text', '')
        title = data.get('title', '')
        news_id = data.get('news_id')

        if not text and news_id:
            news_data = news_service.get_hot_news()
            for category in ['domestic', 'international']:
                if category in news_data:
                    for item in news_data[category]:
                        if str(item.get('link', '')).find(str(news_id)) != -1 or \
                           str(item.get('title', '')).find(str(news_id)) != -1:
                            title = item.get('title', '')
                            content = item.get('content', '') or item.get('description', '') or title
                            text = content
                            break

        if not text and title:
            text = title

        if not text:
            return jsonify(success=False, error='请提供新闻文本、标题或新闻ID'), 400

        news_item = {
            'title': title,
            'content': text,
            'source': data.get('source', ''),
            'region': data.get('region', ''),
            'description': text
        }

        summarizer = get_summarizer()
        result = summarizer.summarize_news(news_item)

        return jsonify({"success": True, "summary": result})

    except Exception as e:
        return jsonify(success=False, error=f'摘要生成失败: {str(e)}'), 500


@app.route('/api/news/analyze/sentiment', methods=['POST'])
def api_analyze_sentiment():
    """分析新闻情感"""
    try:
        data = request.json or {}
        text = data.get('text', '')
        title = data.get('title', '')
        news_id = data.get('news_id')

        if not text and news_id:
            news_data = news_service.get_hot_news()
            for category in ['domestic', 'international']:
                if category in news_data:
                    for item in news_data[category]:
                        if str(item.get('link', '')).find(str(news_id)) != -1 or \
                           str(item.get('title', '')).find(str(news_id)) != -1:
                            title = item.get('title', '')
                            content = item.get('content', '') or item.get('description', '') or title
                            text = content
                            break

        if not text and title:
            text = title

        if not text:
            return jsonify(success=False, error='请提供新闻文本、标题或新闻ID'), 400

        analyzer = get_sentiment_analyzer()
        result = analyzer.analyze_sentiment(text, title)

        return jsonify({"success": True, "sentiment": result})

    except Exception as e:
        return jsonify(success=False, error=f'情感分析失败: {str(e)}'), 500


# ==================== 评论生成（强化） ====================

@app.route('/api/news/analyze/comment', methods=['POST'])
def api_analyze_comment():
    """生成新闻评论（支持多类型）"""
    try:
        data = request.json or {}

        text = data.get('text', '')
        title = data.get('title', '')
        news_id = data.get('news_id')
        comment_type = data.get('comment_type', 'insightful')  # 评论类型参数

        if not text and news_id:
            news_data = news_service.get_hot_news()
            for category in ['domestic', 'international']:
                if category in news_data:
                    for item in news_data[category]:
                        if str(item.get('link', '')).find(str(news_id)) != -1 or \
                           str(item.get('title', '')).find(str(news_id)) != -1:
                            title = item.get('title', '')
                            content = item.get('content', '') or item.get('description', '') or title
                            text = content
                            break

        if not text and title:
            text = title

        if not text:
            return jsonify(success=False, error='请提供新闻文本、标题或新闻ID'), 400

        generator = get_deepseek_generator()
        result = generator.generate_comment_for_news(title, text, news_id, comment_type)

        return jsonify({
            "success": result.success,
            "comment": result.comment,
            "error": result.error,
            "model": result.model,
            "usage_tokens": result.usage_tokens,
            "generation_time": result.generation_time,
            "cached": result.cached,
            "news_id": result.news_id,
            "news_title": result.news_title,
            "comment_type": result.comment_type
        })

    except Exception as e:
        return jsonify(success=False, error=f'评论生成失败: {str(e)}'), 500


@app.route('/api/news/analyze/comment/batch', methods=['POST'])
def api_analyze_comment_batch():
    """批量生成新闻评论"""
    try:
        data = request.json or {}
        news_items = data.get('news_items', [])
        comment_type = data.get('comment_type', 'insightful')

        if not news_items:
            return jsonify(success=False, error='请提供新闻列表'), 400

        validated_items = []
        for i, item in enumerate(news_items):
            title = item.get('title', '')
            if not title:
                return jsonify(success=False, error=f'第{i+1}个新闻项缺少标题'), 400
            validated_items.append({
                'title': title,
                'content': item.get('content', ''),
                'id': item.get('id', f'news_{i}')
            })

        generator = get_deepseek_generator()
        max_concurrent = data.get('max_concurrent', 3)
        results = generator.generate_comments_batch(validated_items, max_concurrent, comment_type)

        results_list = []
        for result in results:
            results_list.append({
                'success': result.success,
                'comment': result.comment,
                'error': result.error,
                'model': result.model,
                'usage_tokens': result.usage_tokens,
                'generation_time': result.generation_time,
                'cached': result.cached,
                'news_id': result.news_id,
                'news_title': result.news_title,
                'comment_type': result.comment_type
            })

        return jsonify({
            "success": True,
            "results": results_list,
            "total": len(results_list),
            "successful": sum(1 for r in results_list if r['success']),
            "failed": sum(1 for r in results_list if not r['success'])
        })

    except Exception as e:
        return jsonify(success=False, error=f'批量评论生成失败: {str(e)}'), 500


# ==================== 新闻改写（新增） ====================

@app.route('/api/news/rewrite', methods=['POST'])
def api_rewrite_news():
    """改写新闻"""
    try:
        data = request.json or {}
        title = data.get('title', '')
        content = data.get('content', '')
        style = data.get('style', 'formal')  # 改写风格参数

        if not title and not content:
            return jsonify(success=False, error='请提供新闻标题或内容'), 400

        generator = get_deepseek_generator()
        result = generator.rewrite_news(title, content, style)

        return jsonify({
            "success": result.success,
            "rewritten_text": result.rewritten_text,
            "error": result.error,
            "model": result.model,
            "usage_tokens": result.usage_tokens,
            "generation_time": result.generation_time,
            "news_title": result.news_title,
            "rewrite_style": result.rewrite_style
        })

    except Exception as e:
        return jsonify(success=False, error=f'新闻改写失败: {str(e)}'), 500


@app.route('/api/news/rewrite/save', methods=['POST'])
def api_save_rewrite():
    """保存改写结果"""
    try:
        data = request.json or {}
        news_title = data.get('news_title', '')
        original_content = data.get('original_content', '')
        rewritten_text = data.get('rewritten_text', '')
        style = data.get('style', 'formal')

        if not rewritten_text:
            return jsonify(success=False, error='没有可保存的改写结果'), 400

        generator = get_deepseek_generator()
        paths = generator.save_rewrite_result(news_title, original_content, rewritten_text, style)

        return jsonify({
            "success": True,
            "json_path": paths["json_path"],
            "txt_path": paths["txt_path"],
            "message": "改写结果已保存"
        })

    except Exception as e:
        return jsonify(success=False, error=f'保存改写结果失败: {str(e)}'), 500


@app.route('/api/news/comment-types', methods=['GET'])
def api_comment_types():
    """获取支持的评论类型列表"""
    try:
        generator = get_deepseek_generator()
        types = generator.get_comment_types_info()
        return jsonify({"success": True, "comment_types": types})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/news/rewrite-styles', methods=['GET'])
def api_rewrite_styles():
    """获取支持的改写风格列表"""
    try:
        generator = get_deepseek_generator()
        styles = generator.get_rewrite_styles_info()
        return jsonify({"success": True, "rewrite_styles": styles})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/news/search-content')
def api_news_search_content():
    """根据新闻标题搜索完整内容"""
    try:
        title = request.args.get('title', '').strip()
        if not title:
            return jsonify(success=False, error='请提供新闻标题'), 400
        
        db = get_database()
        news_list = db.search_news_db(keyword=title, max_results=5)
        
        matched_news = None
        for news in news_list:
            if news.get('title', '').strip() == title:
                matched_news = news
                break
        
        if not matched_news and news_list:
            # 模糊匹配：找最接近的
            matched_news = news_list[0]
        
        if matched_news:
            return jsonify({
                "success": True,
                "news": {
                    "title": matched_news.get('title', ''),
                    "content": matched_news.get('content', '') or matched_news.get('description', ''),
                    "source": matched_news.get('source', ''),
                    "published": matched_news.get('published_at', '')
                }
            })
        else:
            return jsonify(success=False, error='未找到匹配的新闻内容', news=None)
    except Exception as e:
        return jsonify(success=False, error=f'搜索新闻内容失败: {str(e)}'), 500


# ==================== 原有功能保留 ====================

@app.route('/api/deepseek/usage')
def api_deepseek_usage():
    """获取DeepSeek使用量统计"""
    try:
        generator = get_deepseek_generator()
        usage_info = generator.get_usage_info()
        return jsonify({"success": True, "usage_info": usage_info})
    except Exception as e:
        return jsonify(success=False, error=f'获取使用量统计失败: {str(e)}'), 500


@app.route('/api/trend/hotness')
def api_trend_hotness():
    """获取热度趋势数据"""
    try:
        trend_type = request.args.get('type', 'hourly')
        period = request.args.get('period')

        analyzer = get_trend_analyzer()

        if trend_type == 'hourly':
            hours = int(period) if period and period.isdigit() else 24
            result = analyzer.get_hourly_trend(hours)
        elif trend_type == 'daily':
            days = int(period) if period and period.isdigit() else 7
            result = analyzer.get_daily_trend(days)
        elif trend_type == 'weekly':
            weeks = int(period) if period and period.isdigit() else 4
            result = analyzer.get_weekly_trend(weeks)
        else:
            return jsonify(success=False, error='不支持的趋势类型'), 400

        return jsonify(result)

    except Exception as e:
        return jsonify(success=False, error=f'获取趋势数据失败: {str(e)}'), 500


@app.route('/api/trend/statistics')
def api_trend_statistics():
    """获取趋势统计信息"""
    try:
        analyzer = get_trend_analyzer()
        result = analyzer.get_trend_statistics()
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取统计信息失败: {str(e)}'), 500


@app.route('/api/region/distribution')
def api_region_distribution():
    """获取地区分布数据"""
    try:
        dist_type = request.args.get('type', 'country')
        limit = request.args.get('limit', '20')

        analyzer = get_region_analyzer()

        if dist_type == 'country':
            limit_int = int(limit) if limit and limit.isdigit() else 20
            result = analyzer.get_country_distribution(limit_int)
        else:
            return jsonify(success=False, error='不支持的分布类型'), 400

        return jsonify(result)

    except Exception as e:
        return jsonify(success=False, error=f'获取地区分布数据失败: {str(e)}'), 500


@app.route('/api/region/statistics')
def api_region_statistics():
    """获取地区统计信息"""
    try:
        analyzer = get_region_analyzer()
        result = analyzer.get_region_statistics()
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取地区统计信息失败: {str(e)}'), 500


@app.route('/api/region/news/by-country', methods=['GET'])
def api_region_news_by_country():
    """获取指定国家的新闻"""
    try:
        country = request.args.get('country', '')
        limit = request.args.get('limit', '10')
        if not country:
            return jsonify(success=False, error='请提供国家名称'), 400
        limit_int = int(limit) if limit and limit.isdigit() else 10
        analyzer = get_region_analyzer()
        result = analyzer.get_news_by_country(country, limit_int)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取国家新闻失败: {str(e)}'), 500


@app.route('/api/trend')
def api_trend():
    """获取新闻热度趋势数据"""
    try:
        days = request.args.get('days', '30')
        days_int = int(days) if days and days.isdigit() else 30
        
        analyzer = get_trend_analyzer()
        result = analyzer.get_trend_data(days_int)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取趋势数据失败: {str(e)}'), 500


# ==================== 搜索功能增强 ====================

@app.route('/api/news/search')
def api_news_search():
    """全文搜索新闻（标题+内容），支持高级筛选"""
    try:
        keyword = request.args.get('keyword', '').strip()
        category = request.args.get('category', 'all')
        fulltext = request.args.get('fulltext', 'true').lower() in ('true', '1', 'yes')
        time_range = request.args.get('time_range', 'all')
        source = request.args.get('source', '').strip()
        sentiment = request.args.get('sentiment', 'all')

        results = news_service.search_news(
            keyword=keyword,
            category=category,
            fulltext=fulltext,
            time_range=time_range,
            source=source,
            sentiment=sentiment,
            max_results=50
        )

        return jsonify({
            "success": True,
            "results": results,
            "total": len(results),
            "keyword": keyword
        })

    except Exception as e:
        return jsonify(success=False, error=f'搜索失败: {str(e)}'), 500


@app.route('/api/news/sources')
def api_news_sources():
    """获取所有新闻来源列表"""
    try:
        sources = news_service.get_all_sources()
        return jsonify({
            "success": True,
            "sources": sources
        })
    except Exception as e:
        return jsonify(success=False, error=f'获取来源列表失败: {str(e)}'), 500


@app.route('/api/region/news/by-region', methods=['GET'])
def api_region_news_by_region():
    """获取指定地区的新闻"""
    try:
        region = request.args.get('region', '')
        limit = request.args.get('limit', '10')
        if not region:
            return jsonify(success=False, error='请提供地区名称'), 400
        limit_int = int(limit) if limit and limit.isdigit() else 10
        analyzer = get_region_analyzer()
        result = analyzer.get_news_by_region(region, limit_int)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取地区新闻失败: {str(e)}'), 500


@app.route('/api/geocode')
def api_geocode():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    try:
        latitude = float(lat)
        longitude = float(lon)
    except (TypeError, ValueError):
        return jsonify(success=False, error='无效坐标'), 400

    city = location_service.get_city_by_coordinates(latitude, longitude)
    if not city:
        return jsonify(success=False, error='无法解析城市'), 404

    return jsonify(success=True, city=city)


@app.route('/api/wordcloud')
def api_wordcloud():
    """获取新闻词云数据"""
    try:
        # 获取新闻数据
        news_data = news_service.get_hot_news()
        
        # 合并国内和国际新闻
        all_news = []
        if 'domestic' in news_data:
            all_news.extend(news_data['domestic'])
        if 'international' in news_data:
            all_news.extend(news_data['international'])
        
        # 提取关键词
        word_cloud_service = get_word_cloud_service()
        keywords = word_cloud_service.extract_keywords(all_news, top_n=100)
        
        return jsonify({
            "success": True,
            "keywords": keywords
        })
    except Exception as e:
        return jsonify(success=False, error=f'获取词云数据失败: {str(e)}'), 500


# ==================== 实体关系图谱 ====================

@app.route('/api/entity-graph/data')
def api_entity_graph_data():
    """获取实体图谱数据"""
    try:
        min_weight = request.args.get('min_weight', '1')
        min_weight_int = int(min_weight) if min_weight and min_weight.isdigit() else 1
        
        graph = get_entity_graph()
        result = graph.get_full_graph(min_weight_int)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取图谱数据失败: {str(e)}'), 500


@app.route('/api/entity-graph/detail')
def api_entity_graph_detail():
    """获取单个实体详情"""
    try:
        entity_name = request.args.get('name', '').strip()
        if not entity_name:
            return jsonify(success=False, error='请提供实体名称'), 400
        
        graph = get_entity_graph()
        result = graph.get_entity_detail(entity_name)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取实体详情失败: {str(e)}'), 500


@app.route('/api/entity-graph/search')
def api_entity_graph_search():
    """搜索实体"""
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify(success=False, results=[], total=0), 200
        
        graph = get_entity_graph()
        results = graph.search_entities(keyword)
        return jsonify({
            "success": True,
            "results": results,
            "total": len(results)
        })
    except Exception as e:
        return jsonify(success=False, error=f'搜索实体失败: {str(e)}'), 500


@app.route('/api/entity-graph/statistics')
def api_entity_graph_statistics():
    """获取实体图谱统计"""
    try:
        graph = get_entity_graph()
        result = graph.get_entity_statistics()
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取实体统计失败: {str(e)}'), 500


@app.route('/api/entity-graph/process', methods=['POST'])
def api_entity_graph_process():
    """处理当前新闻更新实体图谱和事件追踪"""
    try:
        news_data = news_service.get_hot_news()
        processed = 0
        
        for category in ['domestic', 'international']:
            if category in news_data:
                for item in news_data[category]:
                    try:
                        process_news_for_graph(item)
                        processed += 1
                    except Exception as e:
                        print(f"处理新闻失败: {e}")
                        continue
        
        return jsonify({
            "success": True, 
            "message": f"图谱与事件追踪更新完成，处理了 {processed} 条新闻",
            "processed": processed
        })
    except Exception as e:
        return jsonify(success=False, error=f'更新图谱失败: {str(e)}'), 500


# ==================== 事件追踪 ====================

@app.route('/api/events/list')
def api_events_list():
    """获取事件列表"""
    try:
        status = request.args.get('status', 'all')
        limit = request.args.get('limit', '20')
        limit_int = int(limit) if limit and limit.isdigit() else 20
        
        tracker = get_event_tracker()
        result = tracker.get_event_list(status, limit_int)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取事件列表失败: {str(e)}'), 500


@app.route('/api/events/detail')
def api_events_detail():
    """获取事件详情"""
    try:
        event_id = request.args.get('event_id', '').strip()
        if not event_id:
            return jsonify(success=False, error='请提供事件ID'), 400
        
        tracker = get_event_tracker()
        result = tracker.get_event_detail(event_id)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取事件详情失败: {str(e)}'), 500


@app.route('/api/events/related')
def api_events_related():
    """获取关联事件"""
    try:
        event_id = request.args.get('event_id', '').strip()
        if not event_id:
            return jsonify(success=False, error='请提供事件ID'), 400
        
        tracker = get_event_tracker()
        result = tracker.get_related_events(event_id)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取关联事件失败: {str(e)}'), 500


@app.route('/api/events/timeline')
def api_events_timeline():
    """获取时间线数据"""
    try:
        entity_name = request.args.get('entity', '').strip()
        event_id = request.args.get('event_id', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        
        tracker = get_event_tracker()
        result = tracker.get_timeline(
            entity_name=entity_name if entity_name else None,
            event_id=event_id if event_id else None,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None
        )
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取时间线数据失败: {str(e)}'), 500


@app.route('/api/events/statistics')
def api_events_statistics():
    """获取事件统计"""
    try:
        tracker = get_event_tracker()
        result = tracker.get_event_statistics()
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取事件统计失败: {str(e)}'), 500


# ==================== 实体深度挖掘 ====================

@app.route('/api/entity-miner/profile')
def api_entity_miner_profile():
    """获取实体画像"""
    try:
        entity_name = request.args.get('name', '').strip()
        if not entity_name:
            return jsonify(success=False, error='请提供实体名称'), 400
        
        miner = get_entity_miner()
        graph = get_entity_graph()
        tracker = get_event_tracker()
        
        # 获取实体图谱详情
        graph_data = graph.get_entity_detail(entity_name)
        
        # 获取实体时间线数据
        timeline_data = tracker.get_timeline(entity_name=entity_name)
        
        result = miner.get_profile(entity_name, graph_data, timeline_data)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取实体画像失败: {str(e)}'), 500


@app.route('/api/entity-miner/network')
def api_entity_miner_network():
    """获取实体关联网络"""
    try:
        entity_name = request.args.get('name', '').strip()
        if not entity_name:
            return jsonify(success=False, error='请提供实体名称'), 400
        
        # 先构建画像
        miner = get_entity_miner()
        graph = get_entity_graph()
        tracker = get_event_tracker()
        
        graph_data = graph.get_entity_detail(entity_name)
        
        # 如果实体不存在，先尝试从图谱构建
        if not graph_data.get('success'):
            return jsonify(success=False, error='实体不存在，请先更新图谱')
        
        timeline_data = tracker.get_timeline(entity_name=entity_name)
        miner.get_profile(entity_name, graph_data, timeline_data)
        
        # 获取关联网络
        result = miner.get_entity_network(entity_name)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取关联网络失败: {str(e)}'), 500


@app.route('/api/entity-miner/sentiment-trend')
def api_entity_miner_sentiment():
    """获取实体情感趋势"""
    try:
        entity_name = request.args.get('name', '').strip()
        if not entity_name:
            return jsonify(success=False, error='请提供实体名称'), 400
        
        miner = get_entity_miner()
        result = miner.get_entity_sentiment_trend(entity_name)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取情感趋势失败: {str(e)}'), 500


@app.route('/api/entity-miner/news')
def api_entity_miner_news():
    """获取实体相关新闻"""
    try:
        entity_name = request.args.get('name', '').strip()
        limit = request.args.get('limit', '20')
        limit_int = int(limit) if limit and limit.isdigit() else 20
        
        if not entity_name:
            return jsonify(success=False, error='请提供实体名称'), 400
        
        miner = get_entity_miner()
        result = miner.get_entity_news(entity_name, limit_int)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取实体新闻失败: {str(e)}'), 500


@app.route('/api/entity-miner/timeline')
def api_entity_miner_timeline():
    """获取实体时间线视图数据"""
    try:
        entity_name = request.args.get('name', '').strip()
        if not entity_name:
            return jsonify(success=False, error='请提供实体名称'), 400
        
        miner = get_entity_miner()
        result = miner.get_entity_timeline_data(entity_name)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取时间线数据失败: {str(e)}'), 500


@app.route('/api/entity-miner/search')
def api_entity_miner_search():
    """搜索缓存实体画像"""
    try:
        keyword = request.args.get('keyword', '').strip()
        if not keyword:
            return jsonify(success=False, results=[], total=0), 200
        
        miner = get_entity_miner()
        results = miner.search_entity_profiles(keyword)
        return jsonify({
            "success": True,
            "results": results,
            "total": len(results)
        })
    except Exception as e:
        return jsonify(success=False, error=f'搜索画像失败: {str(e)}'), 500


@app.route('/api/entity-miner/statistics')
def api_entity_miner_statistics():
    """获取实体挖掘统计"""
    try:
        miner = get_entity_miner()
        result = miner.get_entity_statistics()
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, error=f'获取统计失败: {str(e)}'), 500


# ==================== AI深度分析（新增） ====================

@app.route('/api/trend/ai-analysis')
def api_trend_ai_analysis():
    """AI深度分析当前新闻"""
    try:
        force_refresh = request.args.get('force', 'false').lower() in ('true', '1', 'yes')

        # 获取新闻数据
        news_data = news_service.get_hot_news()

        all_news = []
        if 'domestic' in news_data:
            all_news.extend(news_data['domestic'])
        if 'international' in news_data:
            all_news.extend(news_data['international'])

        if not all_news:
            return jsonify(success=False, error='没有新闻数据可供分析'), 400

        analyzer = get_ai_deep_analyzer()
        result = analyzer.analyze_news(all_news, force_refresh=force_refresh)

        return jsonify({
            "success": result.success,
            "analysis": {
                "core_trends": result.core_trends,
                "sentiment_controversy": result.sentiment_controversy,
                "signals": result.signals,
                "entity_opinions": result.entity_opinions,
                "outlook_strategy": result.outlook_strategy
            },
            "model": result.model,
            "generation_time": result.generation_time,
            "cached": result.cached,
            "news_count": result.news_count,
            "error": result.error
        })

    except Exception as e:
        return jsonify(success=False, error=f'AI分析失败: {str(e)}'), 500


# ==================== 新闻六维评分（新增） ====================

@app.route('/api/news/score', methods=['POST'])
def api_news_score():
    """获取新闻六维评分"""
    try:
        data = request.json or {}
        title = data.get('title', '')
        content = data.get('content', '')
        source = data.get('source', '')
        hot_score = data.get('hot_score', 0)

        news_item = {
            "title": title,
            "content": content,
            "source": source,
            "hot_score": hot_score
        }

        scorer = get_news_scorer()
        result = scorer.get_dimension_scores(news_item)

        return jsonify({
            "success": True,
            "scores": result["scores"],
            "details": result["details"],
            "total_score": result["total_score"],
            "dimension_labels": result["dimension_labels"],
            "dimension_weights": result["dimension_weights"]
        })

    except Exception as e:
        return jsonify(success=False, error=f'评分失败: {str(e)}'), 500


@app.route('/api/news/score/batch', methods=['POST'])
def api_news_score_batch():
    """批量获取新闻六维评分"""
    try:
        data = request.json or {}
        news_items = data.get('news_items', [])

        if not news_items:
            # 从当前新闻数据获取
            news_data = news_service.get_hot_news()
            all_news = []
            if 'domestic' in news_data:
                all_news.extend(news_data['domestic'])
            if 'international' in news_data:
                all_news.extend(news_data['international'])
            news_items = all_news

        if not news_items:
            return jsonify(success=False, error='没有新闻数据'), 400

        scorer = get_news_scorer()
        scored = scorer.score_news_batch(news_items)
        top_news = scorer.get_top_news(news_items, top_n=20)

        return jsonify({
            "success": True,
            "scored_news": scored,
            "top_news": top_news,
            "total": len(scored)
        })

    except Exception as e:
        return jsonify(success=False, error=f'批量评分失败: {str(e)}'), 500


# ==================== 加权热点新闻（新增） ====================

@app.route('/api/trend/weighted')
def api_trend_weighted():
    """获取加权排序后的热点新闻"""
    try:
        top_n = request.args.get('top_n', '20')
        top_n_int = int(top_n) if top_n.isdigit() else 20

        # 获取新闻数据
        news_data = news_service.get_hot_news()

        all_news = []
        if 'domestic' in news_data:
            all_news.extend(news_data['domestic'])
        if 'international' in news_data:
            all_news.extend(news_data['international'])

        if not all_news:
            return jsonify(success=False, error='没有新闻数据'), 400

        analyzer = get_trend_analyzer()
        weighted = analyzer.get_weighted_hot_news(all_news, top_n=top_n_int)

        return jsonify({
            "success": True,
            "weighted_news": weighted,
            "total": len(weighted),
            "top_n": top_n_int
        })

    except Exception as e:
        return jsonify(success=False, error=f'获取加权新闻失败: {str(e)}'), 500


# ==================== 舆情监控（Phase 2） ====================

@app.route('/api/notification/send', methods=['POST'])
def api_notification_send():
    """发送通知"""
    try:
        data = request.json or {}
        title = data.get('title', '通知')
        content = data.get('content', '')
        level = data.get('level', 'info')
        source = data.get('source', 'manual')
        channels = data.get('channels', None)  # None表示所有通道

        notifier = get_notification_manager()
        results = notifier.send_alert(
            title=title,
            content=content,
            level=level,
            source=source,
            channels=channels
        )

        return jsonify({
            "success": True,
            "results": results,
            "channel_status": notifier.get_channel_status()
        })

    except Exception as e:
        return jsonify(success=False, error=f'发送通知失败: {str(e)}'), 500


@app.route('/api/notification/history')
def api_notification_history():
    """获取通知历史"""
    try:
        limit = request.args.get('limit', '50')
        level = request.args.get('level', None)
        source = request.args.get('source', None)

        limit_int = int(limit) if limit.isdigit() else 50

        notifier = get_notification_manager()
        history = notifier.get_history(
            limit=limit_int,
            level=level if level and level != 'all' else None,
            source=source if source and source != 'all' else None
        )

        return jsonify({
            "success": True,
            "history": [
                {
                    "title": m.title,
                    "content": m.content[:200],
                    "level": m.level,
                    "timestamp": m.timestamp,
                    "source": m.source
                }
                for m in history
            ],
            "total": len(history),
            "channel_status": notifier.get_channel_status()
        })

    except Exception as e:
        return jsonify(success=False, error=f'获取通知历史失败: {str(e)}'), 500


@app.route('/api/notification/channels')
def api_notification_channels():
    """获取通道状态"""
    try:
        notifier = get_notification_manager()
        return jsonify({
            "success": True,
            "channels": notifier.get_channel_status()
        })
    except Exception as e:
        return jsonify(success=False, error=f'获取通道状态失败: {str(e)}'), 500


@app.route('/api/filter/interests')
def api_filter_interests():
    """获取兴趣过滤配置和过滤结果"""
    try:
        # 获取新闻数据
        news_data = news_service.get_hot_news()

        all_news = []
        if 'domestic' in news_data:
            all_news.extend(news_data['domestic'])
        if 'international' in news_data:
            all_news.extend(news_data['international'])

        ai_filter = get_ai_filter()

        # 获取按兴趣分组的过滤结果
        grouped = ai_filter.get_filtered_by_interest(all_news)
        config = ai_filter.get_config()

        # 格式化为前端可用数据
        interests_data = []
        for interest in config["interests"]:
            name = interest["name"]
            news_list = grouped.get(name, [])
            interests_data.append({
                "name": name,
                "keywords": interest["keywords"],
                "weight": interest["weight"],
                "enabled": interest.get("enabled", True),
                "categories": interest.get("categories", []),
                "news_count": len(news_list),
                "news": [
                    {
                        "title": n["news"]["title"],
                        "score": n["match_score"],
                        "keywords": n["matched_keywords"],
                        "source": n["news"].get("source", "")
                    }
                    for n in news_list[:10]
                ]
            })

        return jsonify({
            "success": True,
            "interests": interests_data,
            "settings": config["settings"],
            "total_news": len(all_news),
            "filtered_news": sum(len(v) for v in grouped.values())
        })

    except Exception as e:
        return jsonify(success=False, error=f'获取兴趣过滤失败: {str(e)}'), 500


@app.route('/api/opinion/analyze', methods=['POST'])
def api_opinion_analyze():
    """执行舆情异常分析"""
    try:
        force = request.args.get('force', 'false').lower() in ('true', '1', 'yes')

        # 获取新闻数据
        news_data = news_service.get_hot_news()

        all_news = []
        if 'domestic' in news_data:
            all_news.extend(news_data['domestic'])
        if 'international' in news_data:
            all_news.extend(news_data['international'])

        if not all_news:
            return jsonify(success=False, error='没有新闻数据'), 400

        # 获取情感数据
        sentiment_data = None
        try:
            analyzer = get_sentiment_analyzer()
            sentiment = analyzer.analyze_sentiment_from_news(all_news, get_all_sentiment=True)
            if isinstance(sentiment, dict):
                sentiment_data = {
                    "positive_ratio": sentiment.get("positive_ratio", 0),
                    "negative_ratio": sentiment.get("negative_ratio", 0),
                    "neutral_ratio": sentiment.get("neutral_ratio", 0),
                }
        except Exception:
            pass

        monitor = get_opinion_monitor()
        alerts = monitor.analyze(all_news, sentiment_data=sentiment_data, force=force)

        return jsonify({
            "success": True,
            "alerts": [
                {
                    "type": a.type,
                    "level": a.level,
                    "title": a.title,
                    "description": a.description,
                    "timestamp": a.timestamp,
                    "metrics": a.metrics
                }
                for a in alerts
            ],
            "alert_count": len(alerts),
            "statistics": monitor.get_alert_statistics()
        })

    except Exception as e:
        return jsonify(success=False, error=f'舆情分析失败: {str(e)}'), 500


@app.route('/api/opinion/alerts')
def api_opinion_alerts():
    """获取舆情告警记录"""
    try:
        limit = request.args.get('limit', '50')
        level = request.args.get('level', None)
        alert_type = request.args.get('type', None)

        limit_int = int(limit) if limit.isdigit() else 50

        monitor = get_opinion_monitor()
        alerts = monitor.get_alerts(
            limit=limit_int,
            level=level if level and level != 'all' else None,
            alert_type=alert_type if alert_type and alert_type != 'all' else None
        )

        return jsonify({
            "success": True,
            "alerts": alerts,
            "total": len(alerts),
            "statistics": monitor.get_alert_statistics()
        })

    except Exception as e:
        return jsonify(success=False, error=f'获取告警失败: {str(e)}'), 500


@app.route('/api/opinion/statistics')
def api_opinion_statistics():
    """获取舆情监控统计"""
    try:
        monitor = get_opinion_monitor()
        return jsonify({
            "success": True,
            "statistics": monitor.get_alert_statistics()
        })
    except Exception as e:
        return jsonify(success=False, error=f'获取舆情统计失败: {str(e)}'), 500


# ==================== Dashboard & Widget 配置（Phase 3/4） ====================

@app.route('/api/dashboard/config')
def api_dashboard_config():
    """获取Widget配置"""
    try:
        dashboard = get_dashboard()
        return jsonify({
            "success": True,
            "widgets": dashboard.get_widgets()
        })
    except Exception as e:
        return jsonify(success=False, error=f'获取配置失败: {str(e)}'), 500


@app.route('/api/dashboard/toggle', methods=['POST'])
def api_dashboard_toggle():
    """切换Widget启用状态"""
    try:
        data = request.json or {}
        name = data.get('name', '')
        enabled = data.get('enabled', True)

        if not name:
            return jsonify(success=False, error='请提供Widget名称'), 400

        dashboard = get_dashboard()
        result = dashboard.toggle_widget(name, enabled)

        return jsonify({
            "success": result,
            "widgets": dashboard.get_widgets()
        })
    except Exception as e:
        return jsonify(success=False, error=f'切换失败: {str(e)}'), 500


@app.route('/api/brief/generate', methods=['POST'])
def api_brief_generate():
    """生成每日简报"""
    try:
        # 获取新闻数据
        news_data = news_service.get_hot_news()

        all_news = []
        if 'domestic' in news_data:
            all_news.extend(news_data['domestic'])
        if 'international' in news_data:
            all_news.extend(news_data['international'])

        if not all_news:
            return jsonify(success=False, error='没有新闻数据'), 400

        gen = get_report_generator()
        brief = gen.generate_daily_brief(all_news)
        html = gen.render_html(brief)
        path = gen.save(brief, html)

        return jsonify({
            "success": True,
            "brief": brief,
            "html": html,
            "saved_path": path
        })
    except Exception as e:
        return jsonify(success=False, error=f'生成简报失败: {str(e)}'), 500


@app.route('/api/scheduler/status')
def api_scheduler_status():
    """获取调度器状态"""
    try:
        scheduler = get_scheduler()
        return jsonify({
            "success": True,
            "running": scheduler._running,
            "tasks": {name: {"enabled": t.enabled, "interval": t.interval_minutes}
                      for name, t in scheduler.tasks.items()}
        })
    except Exception as e:
        return jsonify(success=False, error=f'获取状态失败: {str(e)}'), 500


@app.route('/api/scheduler/start', methods=['POST'])
def api_scheduler_start():
    """启动调度器"""
    try:
        scheduler = get_scheduler()
        scheduler.start()
        return jsonify({"success": True, "message": "调度器已启动"})
    except Exception as e:
        return jsonify(success=False, error=f'启动失败: {str(e)}'), 500


@app.route('/api/scheduler/stop', methods=['POST'])
def api_scheduler_stop():
    """停止调度器"""
    try:
        scheduler = get_scheduler()
        scheduler.stop()
        return jsonify({"success": True, "message": "调度器已停止"})
    except Exception as e:
        return jsonify(success=False, error=f'停止失败: {str(e)}'), 500


def open_browser(url):

    try:
        webbrowser.open(url, new=2, autoraise=True)
    except Exception:
        pass



def main():
    url = 'http://127.0.0.1:5000'
    open_browser(url)
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)


if __name__ == '__main__':
    main()
