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
from deepseek_comment_generator import get_deepseek_generator
from word_cloud_service import get_word_cloud_service

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


def open_browser(url):
    try:
        webbrowser.open(url, new=2, autoraise=True)
    except Exception:
        pass


def main():
    url = 'http://127.0.0.1:5000'
    open_browser(url)
    app.run(host='127.0.0.1', port=5000, debug=False)


if __name__ == '__main__':
    main()
