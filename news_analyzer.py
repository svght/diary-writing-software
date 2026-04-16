#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻分析模块 - 第四阶段优化迭代1
实现基础NLP实体提取功能：
1. 人物提取（姓名+职位）
2. 国家提取
"""

import re
from typing import List, Dict, Any, Optional, Tuple


class NewsAnalyzer:
    """新闻分析器 - 基础实体提取"""
    
    # 国家名称列表（中文和英文）
    COUNTRIES = {
        # 中文国家名称
        '中国', '中华人民共和国', '中華人民共和國',
        '美国', '美利坚合众国', '美國', '美利堅合眾國',
        '俄罗斯', '俄罗斯联邦', '俄羅斯', '俄羅斯聯邦',
        '日本', '日本国', '日本國',
        '韩国', '大韩民国', '韓國', '大韓民國',
        '朝鲜', '朝鲜民主主义人民共和国', '朝鮮', '朝鮮民主主義人民共和國',
        '英国', '大不列颠及北爱尔兰联合王国', '英國', '大不列顛及北愛爾蘭聯合王國',
        '法国', '法兰西共和国', '法國', '法蘭西共和國',
        '德国', '德意志联邦共和国', '德國', '德意志聯邦共和國',
        '意大利', '意大利共和国', '意大利', '意大利共和國',
        '加拿大', '加拿大', 
        '澳大利亚', '澳大利亚联邦', '澳大利亞', '澳大利亞聯邦',
        '印度', '印度共和国', '印度', '印度共和國',
        '巴西', '巴西联邦共和国', '巴西', '巴西聯邦共和國',
        '墨西哥', '墨西哥合众国', '墨西哥', '墨西哥合眾國',
        '南非', '南非共和国', '南非', '南非共和國',
        '埃及', '埃及共和国', '埃及', '埃及共和國',
        '伊朗', '伊朗伊斯兰共和国', '伊朗', '伊朗伊斯蘭共和國',
        '以色列', '以色列国', '以色列', '以色列國',
        '沙特阿拉伯', '沙特阿拉伯王国', '沙烏地阿拉伯', '沙烏地阿拉伯王國',
        '土耳其', '土耳其共和国', '土耳其', '土耳其共和國',
        '乌克兰', '乌克兰', 
        '波兰', '波兰共和国', '波蘭', '波蘭共和國',
        '瑞典', '瑞典王国', '瑞典', '瑞典王國',
        '挪威', '挪威王国', '挪威', '挪威王國',
        '芬兰', '芬兰共和国', '芬蘭', '芬蘭共和國',
        '丹麦', '丹麦王国', '丹麥', '丹麥王國',
        '荷兰', '荷兰王国', '荷蘭', '荷蘭王國',
        '比利时', '比利时王国', '比利時', '比利時王國',
        '瑞士', '瑞士联邦', '瑞士', '瑞士聯邦',
        '奥地利', '奥地利共和国', '奧地利', '奧地利共和國',
        '西班牙', '西班牙王国', '西班牙', '西班牙王國',
        '葡萄牙', '葡萄牙共和国', '葡萄牙', '葡萄牙共和國',
        '希腊', '希腊共和国', '希臘', '希臘共和國',
        '泰国', '泰王国', '泰國', '泰王國',
        '越南', '越南社会主义共和国', '越南', '越南社會主義共和國',
        '菲律宾', '菲律宾共和国', '菲律賓', '菲律賓共和國',
        '马来西亚', '马来西亚', '馬來西亞', 
        '新加坡', '新加坡共和国', '新加坡', '新加坡共和國',
        '印度尼西亚', '印度尼西亚共和国', '印度尼西亞', '印度尼西亞共和國',
        '巴基斯坦', '巴基斯坦伊斯兰共和国', '巴基斯坦', '巴基斯坦伊斯蘭共和國',
        '孟加拉国', '孟加拉人民共和国', '孟加拉國', '孟加拉人民共和國',
        '阿富汗', '阿富汗伊斯兰共和国', '阿富汗', '阿富汗伊斯蘭共和國',
        '伊拉克', '伊拉克共和国', '伊拉克', '伊拉克共和國',
        '叙利亚', '叙利亚共和国', '敘利亞', '敘利亞共和國',
        '约旦', '约旦哈希姆王国', '約旦', '約旦哈希姆王國',
        '黎巴嫩', '黎巴嫩共和国', '黎巴嫩', '黎巴嫩共和國',
        '阿联酋', '阿拉伯联合酋长国', '阿聯酋', '阿拉伯聯合酋長國',
        '卡塔尔', '卡塔尔国', '卡塔爾', '卡塔爾國',
        '科威特', '科威特国', '科威特', '科威特國',
        '阿曼', '阿曼苏丹国', '阿曼', '阿曼蘇丹國',
        '也门', '也门共和国', '也門', '也門共和國',
        '古巴', '古巴共和国', '古巴', '古巴共和國',
        '委内瑞拉', '委内瑞拉玻利瓦尔共和国', '委內瑞拉', '委內瑞拉玻利瓦爾共和國',
        '哥伦比亚', '哥伦比亚共和国', '哥倫比亞', '哥倫比亞共和國',
        '秘鲁', '秘鲁共和国', '秘魯', '秘魯共和國',
        '智利', '智利共和国', '智利', '智利共和國',
        '阿根廷', '阿根廷共和国', '阿根廷', '阿根廷共和國',
        '新西兰', '新西兰', '新西蘭',
        # 英文国家名称
        'China', 'United States', 'USA', 'US', 'America',
        'Russia', 'Japan', 'South Korea', 'Korea',
        'North Korea', 'United Kingdom', 'UK', 'Britain',
        'France', 'Germany', 'Italy', 'Canada', 'Australia',
        'India', 'Brazil', 'Mexico', 'South Africa',
        'Egypt', 'Iran', 'Israel', 'Saudi Arabia',
        'Turkey', 'Ukraine', 'Poland', 'Sweden',
        'Norway', 'Finland', 'Denmark', 'Netherlands',
        'Belgium', 'Switzerland', 'Austria', 'Spain',
        'Portugal', 'Greece', 'Thailand', 'Vietnam',
        'Philippines', 'Malaysia', 'Singapore', 'Indonesia',
        'Pakistan', 'Bangladesh', 'Afghanistan', 'Iraq',
        'Syria', 'Jordan', 'Lebanon', 'United Arab Emirates', 'UAE',
        'Qatar', 'Kuwait', 'Oman', 'Yemen',
        'Cuba', 'Venezuela', 'Colombia', 'Peru',
        'Chile', 'Argentina', 'New Zealand'
    }
    
    # 常见职位/称谓
    POSITIONS = {
        '主席', '总统', '总理', '首相', '国王', '女王', '皇帝', '天皇',
        '部长', '局长', '厅长', '省长', '市长', '县长', '区长',
        '书记', '主任', '校长', '院长', '所长', '社长', '会长',
        '经理', '总监', '主管', '负责人', '代表', '发言人',
        '教授', '博士', '院士', '专家', '学者', '研究员',
        '大使', '领事', '外交官', '特使', '代表',
        '司令', '将军', '军官', '士兵', '警察', '警官',
        '法官', '律师', '检察官', '公证员',
        '医生', '护士', '教师', '工程师', '设计师',
        '运动员', '教练', '裁判', '演员', '歌手', '导演',
        '记者', '编辑', '主持人', '主播', '评论员',
        '董事长', 'CEO', '总经理', '总裁', '创始人',
        '司机', '工人', '农民', '商人', '企业家'
    }
    
    # 已知常见人物（新闻中频繁出现的知名人物）
    KNOWN_PEOPLE = {
        # 中国领导人
        '习近平', '习近平主席', '主席习近平', '国家主席习近平',
        '李克强', '李克强总理', '总理李克强',
        '胡锦涛', '温家宝', '江泽民',
        # 美国总统
        '拜登', '拜登总统', '总统拜登', '乔·拜登', 'Joe Biden',
        '特朗普', '特朗普总统', '总统特朗普', '唐纳德·特朗普', 'Donald Trump',
        '奥巴马', '奥巴马总统', '总统奥巴马', '巴拉克·奥巴马', 'Barack Obama',
        # 俄罗斯领导人
        '普京', '普京总统', '总统普京', '弗拉基米尔·普京', 'Vladimir Putin',
        # 乌克兰领导人
        '泽连斯基', '泽连斯基总统', '总统泽连斯基', '弗拉基米尔·泽连斯基', 'Volodymyr Zelenskyy',
        # 日本领导人
        '岸田文雄', '岸田文雄首相', '首相岸田文雄', 'Fumio Kishida',
        # 英国领导人
        '苏纳克', '苏纳克首相', '首相苏纳克', '里希·苏纳克', 'Rishi Sunak',
        # 法国领导人
        '马克龙', '马克龙总统', '总统马克龙', '埃马纽埃尔·马克龙', 'Emmanuel Macron',
        # 德国领导人
        '朔尔茨', '朔尔茨总理', '总理朔尔茨', '奥拉夫·朔尔茨', 'Olaf Scholz',
        # 其他国际人物
        '莫迪', '莫迪总理', '总理莫迪', '纳伦德拉·莫迪', 'Narendra Modi',
        '金正恩', '金正恩委员长', '委员长金正恩', 'Kim Jong-un',
        '尹锡悦', '尹锡悦总统', '总统尹锡悦', 'Yoon Suk-yeol',
        # 美国官员
        '布林肯', '布林肯国务卿', '国务卿布林肯', '安东尼·布林肯', 'Antony Blinken',
        '哈里斯', '哈里斯副总统', '副总统哈里斯', '卡玛拉·哈里斯', 'Kamala Harris',
        # 中国官员
        '王毅', '王毅外长', '外长王毅', '外交部长王毅',
        '赵立坚', '耿爽',
        # 国际组织
        '古特雷斯', '联合国秘书长古特雷斯', 'António Guterres',
        '世卫组织总干事谭德塞', 'Tedros Adhanom'
    }
    
    def __init__(self):
        """初始化分析器"""
        # 编译正则表达式
        # 中文姓名正则：匹配已知人物（包含中文字符的）
        chinese_names = [name for name in self.KNOWN_PEOPLE if any('\u4e00' <= c <= '\u9fff' for c in name)]
        self.chinese_name_pattern = re.compile(r'(' + '|'.join(re.escape(name) for name in chinese_names) + ')')
        
        # 英文姓名正则：匹配已知英文人物（不包含中文字符的）
        english_names = [name for name in self.KNOWN_PEOPLE if not any('\u4e00' <= c <= '\u9fff' for c in name)]
        self.english_name_pattern = re.compile(r'\b(' + '|'.join(re.escape(name) for name in english_names) + r')\b')
        
    def extract_entities(self, text: str, title: str = "") -> Dict[str, Any]:
        """
        从新闻文本中提取实体
        
        Args:
            text: 新闻正文
            title: 新闻标题（可选）
            
        Returns:
            Dict containing:
                - persons: List of person entities with name and position
                - countries: List of country names
                - entities_text: Combined text for display
        """
        if not text:
            text = title
            
        combined_text = f"{title} {text}" if title else text
        
        # 提取人物
        persons = self._extract_persons(combined_text)
        
        # 提取国家
        countries = self._extract_countries(combined_text)
        
        # 构建展示文本
        entities_text = self._build_entities_text(persons, countries)
        
        return {
            "success": True,
            "persons": persons,
            "countries": countries,
            "entities_text": entities_text,
            "count": len(persons) + len(countries)
        }
    
    def _extract_persons(self, text: str) -> List[Dict[str, str]]:
        """提取人物（姓名+职位）"""
        persons = []
        
        # 方法1：使用正则匹配中文姓名
        chinese_matches = self.chinese_name_pattern.findall(text)
        for name in chinese_matches:
            # 去重
            if not any(p["name"] == name for p in persons):
                position = self._find_adjacent_position(text, name)
                persons.append({
                    "name": name,
                    "position": position if position else "人物",
                    "type": "person"
                })
        
        # 方法2：匹配英文姓名
        english_matches = self.english_name_pattern.findall(text)
        for name in english_matches:
            # 简单判断是否为常见英文姓名（两个大写单词）
            parts = name.split()
            if len(parts) == 2 and parts[0][0].isupper() and parts[1][0].isupper():
                if not any(p["name"] == name for p in persons):
                    position = self._find_adjacent_position(text, name)
                    persons.append({
                        "name": name,
                        "position": position if position else "Person",
                        "type": "person"
                    })
        
        # 去重并返回
        unique_persons = []
        seen = set()
        for person in persons:
            key = person["name"]
            if key not in seen:
                seen.add(key)
                unique_persons.append(person)
                
        return unique_persons
    
    def _find_adjacent_position(self, text: str, name: str) -> Optional[str]:
        """在姓名附近查找职位"""
        if not name or not text:
            return None
            
        # 在姓名前后一定范围内查找职位关键词
        index = text.find(name)
        if index == -1:
            return None
            
        # 查找范围：姓名前后50个字符
        start = max(0, index - 50)
        end = min(len(text), index + len(name) + 50)
        context = text[start:end]
        
        # 在上下文中查找职位关键词
        for position in self.POSITIONS:
            if position in context:
                return position
                
        return None
    
    def _extract_countries(self, text: str) -> List[str]:
        """提取国家名称"""
        found_countries = []
        
        # 简单字符串匹配
        for country in self.COUNTRIES:
            if country in text:
                found_countries.append(country)
        
        # 去重并返回
        return list(dict.fromkeys(found_countries))  # 保持顺序去重
    
    def _build_entities_text(self, persons: List[Dict], countries: List[str]) -> str:
        """构建实体展示文本"""
        parts = []
        
        if persons:
            person_text = "人物：" + "、".join([f"{p['name']}({p['position']})" for p in persons[:5]])  # 最多显示5个
            parts.append(person_text)
            
        if countries:
            country_text = "国家：" + "、".join(countries[:5])  # 最多显示5个
            parts.append(country_text)
            
        return " | ".join(parts) if parts else "未识别到关键实体"


# 全局实例
_analyzer_instance = None

def get_analyzer():
    """获取分析器实例（单例模式）"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = NewsAnalyzer()
    return _analyzer_instance


def extract_entities_from_news(news_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    从新闻项中提取实体（方便函数）
    
    Args:
        news_item: 新闻字典，包含title, source, content等字段
        
    Returns:
        提取结果
    """
    analyzer = get_analyzer()
    
    title = news_item.get('title', '')
    # 尝试获取内容，如果没有则使用标题
    content = news_item.get('content', '') or news_item.get('description', '') or title
    
    return analyzer.extract_entities(content, title)


if __name__ == "__main__":
    # 测试代码
    analyzer = NewsAnalyzer()
    
    test_cases = [
        "习近平主席在北京会见美国总统拜登。",
        "俄罗斯总统普京与乌克兰总统泽连斯基举行会谈。",
        "日本首相岸田文雄访问中国，与李克强总理会面。",
        "The President of the United States Joe Biden met with the Prime Minister of the UK Rishi Sunak.",
        "中国和美国在气候变化问题上达成合作。俄罗斯表示支持。"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"测试 {i}: {text}")
        result = analyzer.extract_entities(text)
        # 修复f-string中的引号转义问题
        person_display = []
        for p in result['persons']:
            person_display.append(f"{p['name']}({p['position']})")
        print(f"  人物: {person_display}")
        print(f"  国家: {result['countries']}")
        print(f"  展示文本: {result['entities_text']}")
        print()
