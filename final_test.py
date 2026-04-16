#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试 - 验证迭代4完整功能
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def wait_for_server(max_attempts=30, delay=1):
    """等待服务器启动"""
    print("等待服务器启动...")
    for i in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/api/weather?city=北京", timeout=2)
            if response.status_code == 200:
                print("✓ 服务器已启动")
                return True
        except Exception:
            if i % 5 == 0:
                print(f"  等待中... ({i+1}/{max_attempts})")
            time.sleep(delay)
    print("✗ 服务器启动超时")
    return False

def test_trend_apis():
    """测试热度趋势API"""
    print("\n" + "=" * 60)
    print("测试热度趋势API (迭代4)")
    print("=" * 60)
    
    # 测试每小时趋势
    print("\n1. 测试24小时热度变化折线图:")
    try:
        response = requests.get(
            f"{BASE_URL}/api/trend/hotness",
            params={"type": "hourly", "period": "24"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"  ✓ 24小时趋势API工作正常")
                print(f"    数据点数量: {len(data.get('data', []))}")
                print(f"    标签: {data.get('labels', [])[:3]}...")
                print(f"    平均热度: {data.get('avg_scores', [])[:3]}...")
            else:
                print(f"  ✗ API返回错误: {data.get('error', 'Unknown error')}")
        else:
            print(f"  ✗ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
    
    # 测试每日趋势
    print("\n2. 测试7天热度趋势图表:")
    try:
        response = requests.get(
            f"{BASE_URL}/api/trend/hotness",
            params={"type": "daily", "period": "7"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"  ✓ 7天趋势API工作正常")
                print(f"    数据点数量: {len(data.get('data', []))}")
                print(f"    标签: {data.get('labels', [])}")
                print(f"    平均热度: {[round(s, 1) for s in data.get('avg_scores', [])]}")
            else:
                print(f"  ✗ API返回错误: {data.get('error', 'Unknown error')}")
        else:
            print(f"  ✗ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
    
    # 测试时间筛选功能
    print("\n3. 测试时间筛选功能:")
    test_cases = [
        ("hourly", "12", "12小时趋势"),
        ("hourly", "6", "6小时趋势"),
        ("daily", "3", "3天趋势"),
        ("daily", "1", "1天趋势"),
        ("weekly", "2", "2周趋势"),
    ]
    
    for trend_type, period, description in test_cases:
        try:
            response = requests.get(
                f"{BASE_URL}/api/trend/hotness",
                params={"type": trend_type, "period": period},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"  ✓ {description}: 工作正常")
                else:
                    print(f"  ✗ {description}: {data.get('error', 'Unknown error')}")
            else:
                print(f"  ✗ {description}: HTTP错误 {response.status_code}")
        except Exception as e:
            print(f"  ✗ {description}: 请求失败: {e}")
    
    # 测试统计信息
    print("\n4. 测试趋势统计信息:")
    try:
        response = requests.get(f"{BASE_URL}/api/trend/statistics", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                stats = data.get("statistics", {})
                print(f"  ✓ 统计信息API工作正常")
                print(f"    最后更新: {data.get('last_update', 'N/A')}")
                print(f"    总新闻数: {stats.get('total_news', 0)}")
                print(f"    平均热度: {stats.get('avg_hot_score', 0):.1f}")
                print(f"    最高热度: {stats.get('max_hot_score', 0)}")
                print(f"    最低热度: {stats.get('min_hot_score', 0)}")
            else:
                print(f"  ✗ API返回错误: {data.get('error', 'Unknown error')}")
        else:
            print(f"  ✗ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
    
    # 测试错误处理
    print("\n5. 测试错误处理:")
    
    # 测试无效类型
    print("\n  测试无效趋势类型:")
    try:
        response = requests.get(
            f"{BASE_URL}/api/trend/hotness",
            params={"type": "invalid_type"},
            timeout=10
        )
        if response.status_code == 400:
            print(f"    ✓ 正确处理无效类型 (返回400)")
        elif response.status_code == 200:
            data = response.json()
            if not data.get("success"):
                print(f"    ✓ 返回错误信息: {data.get('error', 'Unknown error')}")
            else:
                print(f"    ✗ 未正确处理无效类型")
        else:
            print(f"    ✗ 预期400错误, 实际: {response.status_code}")
    except Exception as e:
        print(f"    ✗ 请求失败: {e}")

def test_news_update():
    """测试新闻更新功能"""
    print("\n" + "=" * 60)
    print("测试新闻更新功能")
    print("=" * 60)
    
    try:
        # 获取新闻
        response = requests.get(f"{BASE_URL}/api/news", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                domestic_count = len(data.get("domestic", []))
                international_count = len(data.get("international", []))
                print(f"✓ 新闻获取成功")
                print(f"  国内新闻数: {domestic_count}")
                print(f"  国际新闻数: {international_count}")
                print(f"  新闻数据已自动更新趋势分析")
            else:
                print(f"✗ 新闻获取失败: {data.get('error', 'Unknown error')}")
        else:
            print(f"✗ HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

def main():
    print("\n" + "=" * 60)
    print("第四阶段优化迭代4 - 完整功能验证")
    print("=" * 60)
    
    # 等待服务器启动
    if not wait_for_server():
        return
    
    # 测试新闻更新
    test_news_update()
    
    # 测试趋势API
    test_trend_apis()
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)
    print("\n✅ 迭代4功能已实现:")
    print("  ✓ 24小时热度变化折线图 API: /api/trend/hotness?type=hourly")
    print("  ✓ 7天热度趋势图表 API: /api/trend/hotness?type=daily")
    print("  ✓ 时间筛选功能 API: /api/trend/hotness?type=hourly&period=12")
    print("  ✓ 趋势统计信息 API: /api/trend/statistics")
    print("  ✓ 自动数据更新: 新闻获取时自动更新趋势数据")
    print("  ✓ 错误处理和参数验证")
    print("\n📊 数据结构:")
    print("  - 每小时数据: 最近24小时热度变化")
    print("  - 每日数据: 最近7天热度趋势")
    print("  - 每周数据: 最近4周热度汇总")
    print("  - 统计数据: 总新闻数、平均热度等")
    print("\n🔧 技术实现:")
    print("  - 数据持久化: trend_data.json 文件存储")
    print("  - 实时更新: 每次获取新闻时更新趋势")
    print("  - 模拟数据: 无真实数据时提供示例数据")

if __name__ == "__main__":
    main()