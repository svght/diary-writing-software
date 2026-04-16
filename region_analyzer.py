#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地区分布分析器 - 第四阶段优化迭代5
实现地区分布可视化功能：
1. 国家分布条形图
2. 地区统计饼图
3. 地区数据统计和分析
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

# 地区分类定义
REGION_CATEGORIES = {
    # 亚洲
    "东亚": ["中国", "日本", "韩国", "朝鲜", "蒙古", "台湾", "香港", "澳门"],
    "东南亚": ["越南", "泰国", "菲律宾", "马来西亚", "新加坡", "印度尼西亚", "缅甸", "柬埔寨", "老挝", "文莱", "东帝汶"],
    "南亚": ["印度", "巴基斯坦", "孟加拉国", "斯里兰卡", "尼泊尔", "不丹", "马尔代夫", "阿富汗"],
    "中亚": ["哈萨克斯坦", "乌兹别克斯坦", "吉尔吉斯斯坦", "土库曼斯坦", "塔吉克斯坦"],
    "西亚": ["土耳其", "伊朗", "沙特阿拉伯", "伊拉克", "阿联酋", "以色列", "叙利亚", "约旦", "黎巴嫩", "也门", "阿曼", "卡塔尔", "巴林", "科威特"],
    
    # 欧洲
    "西欧": ["英国", "法国", "德国", "意大利", "西班牙", "葡萄牙", "荷兰", "比利时", "卢森堡", "爱尔兰", "瑞士", "奥地利"],
    "北欧": ["瑞典", "挪威", "芬兰", "丹麦", "冰岛", "爱沙尼亚", "拉脱维亚", "立陶宛"],
    "东欧": ["俄罗斯", "乌克兰", "白俄罗斯", "波兰", "捷克", "斯洛伐克", "匈牙利", "罗马尼亚", "保加利亚", "塞尔维亚", "克罗地亚"],
    "南欧": ["希腊", "塞浦路斯", "马耳他", "阿尔巴尼亚", "波斯尼亚和黑塞哥维那", "黑山", "北马其顿", "斯洛文尼亚"],
    
    # 美洲
    "北美": ["美国", "加拿大", "墨西哥"],
    "南美": ["巴西", "阿根廷", "智利", "秘鲁", "哥伦比亚", "委内瑞拉", "乌拉圭", "巴拉圭", "玻利维亚", "厄瓜多尔", "圭亚那", "苏里南"],
    "中美洲": ["巴拿马", "哥斯达黎加", "尼加拉瓜", "洪都拉斯", "萨尔瓦多", "危地马拉", "伯利兹"],
    "加勒比地区": ["古巴", "牙买加", "海地", "多米尼加共和国", "巴哈马", "巴巴多斯", "特立尼达和多巴哥"],
    
    # 非洲
    "北非": ["埃及", "阿尔及利亚", "摩洛哥", "突尼斯", "利比亚", "苏丹", "南苏丹"],
    "西非": ["尼日利亚", "加纳", "科特迪瓦", "塞内加尔", "马里", "布基纳法索", "几内亚", "贝宁", "尼日尔", "多哥"],
    "东非": ["埃塞俄比亚", "肯尼亚", "坦桑尼亚", "乌干达", "卢旺达", "布隆迪", "索马里", "厄立特里亚", "吉布提"],
    "中非": ["刚果(金)", "刚果(布)", "喀麦隆", "乍得", "中非共和国", "加蓬", "赤道几内亚", "圣多美和普林西比"],
    "南非": ["南非", "纳米比亚", "博茨瓦纳", "津巴布韦", "赞比亚", "马拉维", "莫桑比克", "马达加斯加", "毛里求斯", "塞舌尔"],
    
    # 大洋洲
    "大洋洲": ["澳大利亚", "新西兰", "巴布亚新几内亚", "斐济", "所罗门群岛", "瓦努阿图", "萨摩亚", "汤加", "密克罗尼西亚"],
    
    # 其他
    "国际组织": ["联合国", "北约", "欧盟", "东盟", "非盟", "世卫组织", "世贸组织", "国际货币基金组织"],
    "全球": ["全球", "世界", "国际", "环球"],
}


class RegionAnalyzer:
    """地区分布分析器"""
    
    def __init__(self, data_file="region_data.json"):
        """
        初始化地区分析器
        
        Args:
            data_file: 数据存储文件路径
        """
        self.data_file = data_file
        self.region_data = self._load_data()
        
        # 构建国家到地区的映射
        self.country_to_region = {}
        for region, countries in REGION_CATEGORIES.items():
            for country in countries:
                self.country_to_region[country] = region
        
        # 添加别名映射
        self._add_aliases()
    
    def _add_aliases(self):
        """添加国家别名映射"""
        aliases = {
            "美国": ["美利坚合众国", "美國", "美利堅合眾國", "United States", "USA", "US"],
            "中国": ["中华人民共和国", "中華人民共和國", "China", "PRC"],
            "俄罗斯": ["俄罗斯联邦", "俄羅斯", "俄羅斯聯邦", "Russia", "Russian Federation"],
            "日本": ["日本国", "日本國", "Japan"],
            "韩国": ["大韩民国", "韓國", "大韓民國", "South Korea", "Korea"],
            "英国": ["大不列颠及北爱尔兰联合王国", "英國", "大不列顛及北愛爾蘭聯合王國", "United Kingdom", "UK"],
            "法国": ["法兰西共和国", "法國", "法蘭西共和國", "France"],
            "德国": ["德意志联邦共和国", "德國", "德意志聯邦共和國", "Germany"],
            "意大利": ["意大利共和国", "意大利", "意大利共和國", "Italy"],
            "加拿大": ["Canada"],
            "澳大利亚": ["澳大利亚联邦", "澳大利亞", "澳大利亞聯邦", "Australia"],
            "印度": ["印度共和国", "印度", "印度共和國", "India"],
        }
        
        for standard_name, alias_list in aliases.items():
            for alias in alias_list:
                if standard_name in self.country_to_region:
                    self.country_to_region[alias] = self.country_to_region[standard_name]
    
    def _load_data(self) -> Dict:
        """加载地区数据"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载地区数据失败: {e}")
        
        # 返回默认数据结构
        return {
            "country_distribution": {},
            "region_distribution": {},
            "news_by_country": {},
            "news_by_region": {},
            "last_update": None,
            "statistics": {
                "total_news": 0,
                "total_countries": 0,
                "total_regions": 0,
                "most_frequent_country": None,
                "most_frequent_region": None,
            }
        }
    
    def _save_data(self):
        """保存地区数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.region_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存地区数据失败: {e}")
    
    def extract_countries_from_text(self, text: str) -> List[str]:
        """
        从文本中提取国家名称
        
        Args:
            text: 输入文本
            
        Returns:
            提取到的国家名称列表
        """
        if not text:
            return []
        
        found_countries = []
        
        # 检查所有国家名称
        all_countries = []
        for countries in REGION_CATEGORIES.values():
            all_countries.extend(countries)
        
        # 按长度排序，优先匹配长名称
        all_countries_sorted = sorted(all_countries, key=len, reverse=True)
        
        text_lower = text.lower()
        
        for country in all_countries_sorted:
            # 检查中文名称
            if country in text:
                found_countries.append(country)
                # 标记已匹配的部分（简化处理）
                text = text.replace(country, "")
            
            # 检查常见英文名称
            elif country in ["中国", "美国", "俄罗斯", "日本", "韩国", "英国", "法国", "德国", "意大利", "加拿大", "澳大利亚", "印度"]:
                # 添加简单英文匹配逻辑
                english_names = {
                    "中国": ["china", "chinese"],
                    "美国": ["united states", "usa", "us", "america"],
                    "俄罗斯": ["russia", "russian"],
                    "日本": ["japan", "japanese"],
                    "韩国": ["korea", "south korea", "korean"],
                    "英国": ["united kingdom", "uk", "britain", "england"],
                    "法国": ["france", "french"],
                    "德国": ["germany", "german"],
                    "意大利": ["italy", "italian"],
                    "加拿大": ["canada", "canadian"],
                    "澳大利亚": ["australia", "australian"],
                    "印度": ["india", "indian"],
                }
                
                if country in english_names:
                    for en_name in english_names[country]:
                        if en_name in text_lower:
                            found_countries.append(country)
                            break
        
        # 去重并返回
        return list(set(found_countries))
    
    def categorize_by_region(self, countries: List[str]) -> Dict[str, List[str]]:
        """
        将国家按地区分类
        
        Args:
            countries: 国家列表
            
        Returns:
            按地区分类的国家字典
        """
        region_map = {}
        
        for country in countries:
            region = self.country_to_region.get(country)
            if region:
                if region not in region_map:
                    region_map[region] = []
                region_map[region].append(country)
            else:
                # 未识别的国家归入"其他"
                if "其他" not in region_map:
                    region_map["其他"] = []
                region_map["其他"].append(country)
        
        return region_map
    
    def update_with_news(self, news_items: List[Dict]) -> Dict:
        """
        使用新闻数据更新地区分布
        
        Args:
            news_items: 新闻数据列表
            
        Returns:
            更新统计结果
        """
        all_countries = []
        country_news_map = {}
        
        for news in news_items:
            # 提取新闻中的国家信息
            title = news.get('title', '')
            content = news.get('content', '') or news.get('description', '') or ''
            source = news.get('source', '')
            region = news.get('region', '')
            
            # 组合文本进行分析
            text_to_analyze = f"{title} {content} {source} {region}"
            
            # 提取国家
            countries = self.extract_countries_from_text(text_to_analyze)
            all_countries.extend(countries)
            
            # 统计每个国家的新闻
            for country in countries:
                if country not in country_news_map:
                    country_news_map[country] = []
                country_news_map[country].append({
                    'title': title,
                    'source': source,
                    'link': news.get('link', ''),
                    'published': news.get('published', ''),
                })
        
        # 计算国家分布
        country_counter = Counter(all_countries)
        country_distribution = dict(country_counter)
        
        # 计算地区分布
        region_counter = Counter()
        for country, count in country_counter.items():
            region = self.country_to_region.get(country, "其他")
            region_counter[region] += count
        
        region_distribution = dict(region_counter)
        
        # 更新数据
        self.region_data["country_distribution"] = country_distribution
        self.region_data["region_distribution"] = region_distribution
        self.region_data["news_by_country"] = country_news_map
        
        # 按地区组织新闻
        region_news_map = {}
        for country, news_list in country_news_map.items():
            region = self.country_to_region.get(country, "其他")
            if region not in region_news_map:
                region_news_map[region] = []
            region_news_map[region].extend(news_list)
        
        self.region_data["news_by_region"] = region_news_map
        
        # 更新统计信息
        self.region_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 计算统计数据
        if country_distribution:
            most_common_country = max(country_distribution.items(), key=lambda x: x[1])
            most_common_region = max(region_distribution.items(), key=lambda x: x[1])
        else:
            most_common_country = (None, 0)
            most_common_region = (None, 0)
        
        self.region_data["statistics"] = {
            "total_news": len(news_items),
            "total_countries": len(country_distribution),
            "total_regions": len(region_distribution),
            "most_frequent_country": {
                "name": most_common_country[0],
                "count": most_common_country[1]
            } if most_common_country[0] else None,
            "most_frequent_region": {
                "name": most_common_region[0],
                "count": most_common_region[1]
            } if most_common_region[0] else None,
            "avg_news_per_country": len(news_items) / max(1, len(country_distribution)),
        }
        
        # 保存数据
        self._save_data()
        
        return self.get_region_statistics()
    
    def get_country_distribution(self, limit: int = 20) -> Dict:
        """
        获取国家分布数据（用于条形图）
        
        Args:
            limit: 返回的国家数量限制
            
        Returns:
            国家分布数据
        """
        country_dist = self.region_data.get("country_distribution", {})
        
        # 按频率排序
        sorted_countries = sorted(
            country_dist.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        countries = [item[0] for item in sorted_countries]
        counts = [item[1] for item in sorted_countries]
        
        return {
            "success": True,
            "type": "country_distribution",
            "countries": countries,
            "counts": counts,
            "total_countries": len(country_dist),
            "total_news": sum(country_dist.values()) if country_dist else 0,
            "data": [
                {
                    "country": country,
                    "count": count,
                    "region": self.country_to_region.get(country, "其他")
                }
                for country, count in sorted_countries
            ]
        }
    
    def get_region_distribution(self) -> Dict:
        """
        获取地区分布数据（用于饼图）
        
        Returns:
            地区分布数据
        """
        region_dist = self.region_data.get("region_distribution", {})
        
        # 过滤掉数量为0的地区
        filtered_regions = {k: v for k, v in region_dist.items() if v > 0}
        
        regions = list(filtered_regions.keys())
        counts = list(filtered_regions.values())
        
        return {
            "success": True,
            "type": "region_distribution",
            "regions": regions,
            "counts": counts,
            "total_regions": len(filtered_regions),
            "total_news": sum(filtered_regions.values()) if filtered_regions else 0,
            "data": [
                {
                    "region": region,
                    "count": count,
                    "percentage": round(count / max(1, sum(filtered_regions.values())) * 100, 1)
                }
                for region, count in filtered_regions.items()
            ]
        }
    
    def get_region_statistics(self) -> Dict:
        """
        获取地区统计信息
        
        Returns:
            地区统计信息
        """
        stats = self.region_data.get("statistics", {})
        
        return {
            "success": True,
            "last_update": self.region_data.get("last_update"),
            "statistics": stats,
            "country_count": len(self.region_data.get("country_distribution", {})),
            "region_count": len(self.region_data.get("region_distribution", {})),
        }
    
    def get_news_by_country(self, country: str, limit: int = 10) -> Dict:
        """
        获取指定国家的新闻
        
        Args:
            country: 国家名称
            limit: 返回新闻数量限制
            
        Returns:
            国家相关新闻
        """
        news_by_country = self.region_data.get("news_by_country", {})
        
        if country not in news_by_country:
            return {
                "success": False,
                "error": f"未找到国家 '{country}' 的相关新闻"
            }
        
        news_list = news_by_country[country][:limit]
        
        return {
            "success": True,
            "country": country,
            "region": self.country_to_region.get(country, "其他"),
            "news_count": len(news_list),
            "total_count": len(news_by_country[country]),
            "news": news_list
        }
    
    def get_news_by_region(self, region: str, limit: int = 10) -> Dict:
        """
        获取指定地区的新闻
        
        Args:
            region: 地区名称
            limit: 返回新闻数量限制
            
        Returns:
            地区相关新闻
        """
        news_by_region = self.region_data.get("news_by_region", {})
        
        if region not in news_by_region:
            return {
                "success": False,
                "error": f"未找到地区 '{region}' 的相关新闻"
            }
        
        news_list = news_by_region[region][:limit]
        
        return {
            "success": True,
            "region": region,
            "news_count": len(news_list),
            "total_count": len(news_by_region[region]),
            "news": news_list
        }
    
    def clear_data(self):
        """清空地区数据"""
        self.region_data = {
            "country_distribution": {},
            "region_distribution": {},
            "news_by_country": {},
            "news_by_region": {},
            "last_update": None,
            "statistics": {
                "total_news": 0,
                "total_countries": 0,
                "total_regions": 0,
                "most_frequent_country": None,
                "most_frequent_region": None,
            }
        }
        self._save_data()


def get_region_analyzer(data_file="region_data.json") -> RegionAnalyzer:
    """
    获取地区分析器实例（单例模式）
    
    Args:
        data_file: 数据存储文件路径
        
    Returns:
        地区分析器实例
    """
    if not hasattr(get_region_analyzer, "_instance"):
        get_region_analyzer._instance = RegionAnalyzer(data_file)
    return get_region_analyzer._instance


def update_region_with_news(news_items: List[Dict]) -> Dict:
    """
    使用新闻数据更新地区分布
    
    Args:
        news_items: 新闻数据列表
        
    Returns:
        更新结果
    """
    analyzer = get_region_analyzer()
    return analyzer.update_with_news(news_items)


if __name__ == "__main__":
    # 测试代码
    analyzer = RegionAnalyzer()
    
    # 测试文本分析
    test_text = "美国总统拜登访问日本，与中国领导人会谈，讨论俄罗斯和乌克兰局势。"
    countries = analyzer.extract_countries_from_text(test_text)
    print(f"提取到的国家: {countries}")
    
    # 测试地区分类
    region_map = analyzer.categorize_by_region(countries)
    print(f"地区分类: {region_map}")
    
    # 测试数据更新
    test_news = [
        {
            "title": "中美关系新动向",
            "content": "美国总统与中国领导人举行视频会谈",
            "source": "新华网",
            "region": "国际",
            "link": "https://example.com/1",
            "published": "2026-04-16 10:00:00"
        },
        {
            "title": "俄乌局势更新",
            "content": "俄罗斯与乌克兰在边境地区进行谈判",
            "source": "BBC",
            "region": "国际",
            "link": "https://example.com/2",
            "published": "2026-04-16 09:00:00"
        },
        {
            "title": "日本经济政策",
            "content": "日本央行宣布新的货币政策",
            "source": "日经新闻",
            "region": "国际",
            "link": "https://example.com/3",
            "published": "2026-04-16 08:00:00"
        }
    ]
    
    result = analyzer.update_with_news(test_news)
    print(f"\n更新结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
    
    # 测试获取分布数据
    country_dist = analyzer.get_country_distribution()
    print(f"\n国家分布: {country_dist}")
    
    region_dist = analyzer.get_region_distribution()
    print(f"\n地区分布: {region_dist}")