#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试API端点
"""

import requests
import time

BASE_URL = "http://127.0.0.1:5000"

def test_endpoint(endpoint, params=None):
    url = BASE_URL + endpoint
    print(f"\n测试 {endpoint}...")
    try:
        start = time.time()
        response = requests.get(url, params=params, timeout=10)
        elapsed = (time.time() - start) * 1000
        
        print(f"  状态码: {response.status_code}")
        print(f"  耗时: {elapsed:.2f}ms")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  响应: {data.get('success', 'unknown')}")
                if data.get('success'):
                    print(f"   ✓ 成功")
                else:
                    print(f"   ✗ 失败: {data.get('error', 'unknown error')}")
            except:
                print(f"  响应内容: {response.text[:200]}...")
        elif response.status_code == 404:
            print(f"   ✗ 端点未找到 (404)")
        else:
            print(f"   ✗ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")

def main():
    print("快速测试API端点")
    print("=" * 60)
    
    # 测试基础端点
    test_endpoint("/api/weather", {"city": "北京"})
    test_endpoint("/api/news")
    
    # 测试趋势端点
    test_endpoint("/api/trend/hotness", {"type": "hourly", "period": "24"})
    test_endpoint("/api/trend/hotness", {"type": "daily", "period": "7"})
    test_endpoint("/api/trend/hotness", {"type": "weekly", "period": "4"})
    test_endpoint("/api/trend/statistics")
    
    # 测试其他分析端点
    test_endpoint("/api/news/analyze/entities")
    test_endpoint("/api/news/analyze/summary")
    test_endpoint("/api/news/analyze/sentiment")
    
    print("\n" + "=" * 60)
    print("测试完成")

if __name__ == "__main__":
    main()