import re
import time
import requests
from xml.etree import ElementTree as ET


class NewsService:
    """新闻服务类，自动抓取国内与国际热点新闻。"""

    DOMESTIC_TOUTIAO_URL = "https://www.toutiao.com/api/pc/feed/?category=news_hot&max_behot_time=0"
    INTERNATIONAL_FEED_URL = "https://feeds.npr.org/1004/rss.xml"
    INTERNATIONAL_BBC_URL = "https://feeds.bbci.co.uk/news/rss.xml"
    INTERNATIONAL_REUTERS_URL = "https://feeds.reuters.com/Reuters/worldNews"
    DOMESTIC_WEIBO_URL = "https://rss.sina.com.cn/news/society/focus15.xml"  # Using Sina society news as proxy for Weibo social content

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def _fetch_feed(self, url, timeout=5):
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.RequestException:
            return None

    def _fetch_json(self, url, timeout=5):
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    @staticmethod
    def _remove_lone_surrogates(text: str) -> str:
        """移除可能导致JSON解析错误的单独代理项（lone surrogate characters）"""
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        # 移除孤立的高代理项（后面没有低代理项）
        text = re.sub(r'[\uD800-\uDBFF](?![\uDC00-\uDFFF])', '', text)
        # 移除孤立的低代理项（前面没有高代理项）
        text = re.sub(r'(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]', '', text)
        return text

    def _clean_text(self, value):
        if not value:
            return ''
        text = str(value)
        # 先移除lone surrogate字符
        text = self._remove_lone_surrogates(text)
        # 压缩空白
        return ' '.join(text.split())

    def _parse_rss(self, xml_text, max_items=10):
        items = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return items

        channel = root.find('channel')
        feed_title = ''
        if channel is not None:
            title_elem = channel.find('title')
            if title_elem is not None:
                feed_title = self._clean_text(title_elem.text)

            for entry in channel.findall('item')[:max_items]:
                title = self._clean_text(entry.findtext('title'))
                link = self._clean_text(entry.findtext('link'))
                if link.startswith('http://go.rss.sina.com.cn/redirect.php?url='):
                    link = link.split('url=', 1)[1]
                pub_date = self._clean_text(entry.findtext('pubDate'))
                source_elem = entry.find('source')
                source = self._clean_text(source_elem.text) if source_elem is not None and source_elem.text else feed_title
                if title and link:
                    # 第二阶段优化：添加地区分类和质量评分
                    region = self._classify_region(title, source)
                    quality_score = self._calculate_quality_score(title, source, pub_date, region)
                    source_weight = self._get_source_weight(source)
                    # 国际新闻热度分数：基于发布时间和质量评分
                    hot_score = self._calculate_international_hot_score(pub_date, quality_score, region)

                    items.append({
                        'title': title,
                        'link': link,
                        'published': pub_date,
                        'source': source,
                        'region': region,
                        'quality_score': quality_score,
                        'hot_score': hot_score,
                        'source_weight': source_weight,
                        'original_source': source,
                    })
        return items

    def _is_toutiao_ad(self, entry):
        if not isinstance(entry, dict):
            return False

        if entry.get('is_feed_ad'):
            return True
        if entry.get('advertise_info'):
            return True

        title = str(entry.get('title') or '').lower()
        source = str(entry.get('source') or '').lower()
        media_name = str(entry.get('media_name') or '').lower()
        tag_url = str(entry.get('tag_url') or '').lower()

        if '广告' in title or '推广' in title or '软文' in title:
            return True
        if '广告' in source or '推广' in source or '软文' in source:
            return True
        if '广告' in media_name or '推广' in media_name:
            return True
        if 'keyword=广告' in tag_url or 'keyword=推广' in tag_url:
            return True
        if entry.get('group_source') == 1:
            return True

        return False

    def _calculate_toutiao_score(self, entry):
        score = 0
        try:
            comments = int(entry.get('comments_count') or 0)
        except (TypeError, ValueError):
            comments = 0

        now_ts = int(time.time())
        try:
            behot_time = int(entry.get('behot_time') or now_ts)
        except (TypeError, ValueError):
            behot_time = now_ts
        age_hours = max((now_ts - behot_time) / 3600, 0.1)

        # 最新权重：时间越近得分越高
        score += max(0, 48 - age_hours) * 4

        # 评论热度 + 评论增量近似
        score += comments * 2
        score += min(comments / age_hours, 40)

        title = str(entry.get('title') or '').lower()
        abstract = str(entry.get('abstract') or '').lower()
        controversy_keywords = [
            '争议', '质疑', '反对', '投诉', '曝光', '争论', '骂', '谣言', '涉事', '涉嫌',
            '分歧', '抵制', '官宣', '风波', '起诉', '断供', '封杀', '翻车', '停产',
            '暴跌', '暴涨', '举报', '维权', '假货', '事故', '热议', '舆情', '民生',
            '社会', '事件', '安全', '诈骗', '交通', '食品', '医疗', '教育', '住房'
        ]
        for keyword in controversy_keywords:
            if keyword in title or keyword in abstract:
                score += 120

        if '？' in title or '?' in title:
            score += 40
        if '曝光' in title or '曝' in title:
            score += 30
        if '热议' in title or '热度' in title:
            score += 20

        if entry.get('group_source') == 2:
            score += 10

        return score

    def _is_social_topic(self, entry):
        title = str(entry.get('title') or '').lower()
        abstract = str(entry.get('abstract') or '').lower()
        tag = str(entry.get('tag') or '').lower()
        tag_url = str(entry.get('tag_url') or '').lower()
        social_keywords = [
            '社会', '民生', '政治', '军事', '经济', '国防', '军队', '外交', '官方', '政策',
            '舆情', '抗议', '纠纷', '维权', '事故', '安全', '曝光', '热点',
            '搞笑', '段子', '趣闻', '幽默', '娱乐', '明星', '八卦', '趣事'
        ]
        for keyword in social_keywords:
            if keyword in title or keyword in abstract or keyword in tag or keyword in tag_url:
                return True
        return False

    def _parse_toutiao_hot(self, data, max_items=10):
        items = []
        if not isinstance(data, dict):
            return items

        raw_items = data.get('data') or []
        social_items = []
        backup_items = []
        for entry in raw_items:
            if self._is_toutiao_ad(entry):
                continue

            try:
                behot_time = int(entry.get('behot_time') or 0)
            except (TypeError, ValueError):
                continue
            age_seconds = int(time.time()) - behot_time
            if age_seconds < 0 or age_seconds > 48 * 3600:
                continue

            title = self._clean_text(entry.get('title'))
            if not title:
                continue

            score = self._calculate_toutiao_score(entry)
            scored_entry = (score, entry)

            if self._is_social_topic(entry):
                social_items.append(scored_entry)
            else:
                backup_items.append(scored_entry)

        social_items.sort(key=lambda item: item[0], reverse=True)
        backup_items.sort(key=lambda item: item[0], reverse=True)

        combined = social_items + backup_items
        for score, entry in combined:
            if len(items) >= max_items:
                break

            title = self._clean_text(entry.get('title'))
            source = self._clean_text(entry.get('source') or entry.get('media_name') or '今日头条')
            source_url = entry.get('source_url') or ''
            link = ''
            if source_url:
                if source_url.startswith('http'):
                    link = source_url
                else:
                    link = f'https://www.toutiao.com{source_url}'
            elif entry.get('display_url'):
                link = entry.get('display_url')
            else:
                item_id = entry.get('item_id')
                if item_id:
                    link = f'https://www.toutiao.com/a{item_id}'

            published = ''
            behot_time = entry.get('behot_time')
            if behot_time:
                try:
                    from datetime import datetime
                    published = datetime.fromtimestamp(int(behot_time)).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    published = str(behot_time)

            if title and link:
                # 为国内新闻添加地区分类、质量评分和热度分数
                region = self._classify_domestic_region(title)
                quality_score = self._calculate_quality_score(title, source, published, region)
                # 热度分数：使用_calculate_toutiao_score计算的热度分数
                hot_score = score  # _calculate_toutiao_score计算的热度分数
                items.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'source': source,
                    'region': region,
                    'quality_score': quality_score,
                    'hot_score': hot_score,
                    'source_weight': 15,
                    'original_source': source,
                })

        return items


    def _classify_region(self, title, source):
        """根据新闻标题和来源分类地区（主要针对国际新闻）"""
        title_lower = title.lower()
        source_lower = source.lower()

        # 北美相关关键词
        north_america_keywords = [
            'us', 'u.s.', 'united states', 'america', 'american', 'washington', 'new york', 'california',
            'texas', 'canada', 'trump', 'biden', 'white house', 'congress', 'senate', 'house',
            'north america', 'chicago', 'los angeles', 'miami', 'boston', 'detroit'
        ]

        # 欧洲相关关键词
        europe_keywords = [
            'europe', 'european', 'eu', 'uk', 'britain', 'british', 'london', 'england', 'france', 'french',
            'paris', 'germany', 'german', 'berlin', 'italy', 'italian', 'rome', 'spain', 'spanish', 'madrid',
            'russia', 'russian', 'moscow', 'ukraine', 'kyiv', 'poland', 'warsaw', 'sweden', 'stockholm',
            'norway', 'oslo', 'finland', 'helsinki', 'denmark', 'copenhagen'
        ]

        # 亚洲相关关键词
        asia_keywords = [
            'asia', 'asian', 'china', 'chinese', 'beijing', 'shanghai', 'hong kong', 'taiwan', 'japan',
            'japanese', 'tokyo', 'south korea', 'seoul', 'north korea', 'pyongyang', 'india', 'indian',
            'delhi', 'mumbai', 'pakistan', 'islamabad', 'bangladesh', 'dhaka', 'vietnam', 'hanoi',
            'singapore', 'malaysia', 'kuala lumpur', 'thailand', 'bangkok', 'philippines', 'manila'
        ]

        # 中东相关关键词
        middle_east_keywords = [
            'middle east', 'israel', 'israeli', 'jerusalem', 'tel aviv', 'palestine', 'palestinian',
            'gaza', 'west bank', 'iran', 'iranian', 'tehran', 'iraq', 'baghdad', 'syria', 'damascus',
            'saudi arabia', 'riyadh', 'uae', 'dubai', 'qatar', 'doha', 'egypt', 'cairo',
            'lebanon', 'beirut', 'jordan', 'amman', 'turkey', 'ankara', 'istanbul'
        ]

        # 全球相关关键词
        global_keywords = [
            'global', 'world', 'international', 'climate', 'environment', 'pandemic', 'covid',
            'united nations', 'un', 'world health', 'who', 'world bank', 'imf', 'global warming'
        ]

        # 检查关键词
        for keyword in north_america_keywords:
            if keyword in title_lower or keyword in source_lower:
                return '北美'

        for keyword in europe_keywords:
            if keyword in title_lower or keyword in source_lower:
                return '欧洲'

        for keyword in asia_keywords:
            if keyword in title_lower or keyword in source_lower:
                return '亚洲'

        for keyword in middle_east_keywords:
            if keyword in title_lower or keyword in source_lower:
                return '中东'

        for keyword in global_keywords:
            if keyword in title_lower or keyword in source_lower:
                return '全球'

        # 默认分类
        return '其他'

    def _classify_domestic_region(self, title):
        """根据新闻标题分类国内地区"""
        title_lower = title.lower()

        # 中国省份和城市关键词
        regions = {
            '北京': ['北京', 'beijing', '首都', '央视', '中央', '中南海', '天安门'],
            '上海': ['上海', 'shanghai', '浦东', '浦西', '东方明珠'],
            '广东': ['广东', '广州', '深圳', 'guangdong', 'guangzhou', 'shenzhen', '珠三角', '大湾区'],
            '浙江': ['浙江', '杭州', '宁波', 'zhejiang', 'hangzhou', 'ningbo', '阿里巴巴'],
            '江苏': ['江苏', '南京', '苏州', 'jiangsu', 'nanjing', 'suzhou', '无锡'],
            '四川': ['四川', '成都', 'sichuan', 'chengdu', '天府', '川'],
            '重庆': ['重庆', 'chongqing', '山城'],
            '天津': ['天津', 'tianjin'],
            '湖北': ['湖北', '武汉', 'hubei', 'wuhan'],
            '陕西': ['陕西', '西安', 'shaanxi', 'xi\'an', '西安'],
            '河南': ['河南', '郑州', 'henan', 'zhengzhou'],
            '山东': ['山东', '济南', '青岛', 'shandong', 'jinan', 'qingdao'],
            '福建': ['福建', '厦门', '福州', 'fujian', 'xiamen', 'fuzhou'],
            '湖南': ['湖南', '长沙', 'hunan', 'changsha'],
            '安徽': ['安徽', '合肥', 'anhui', 'hefei'],
            '辽宁': ['辽宁', '沈阳', '大连', 'liaoning', 'shenyang', 'dalian'],
            '吉林': ['吉林', '长春', 'jilin', 'changchun'],
            '黑龙江': ['黑龙江', '哈尔滨', 'heilongjiang', 'harbin'],
            '河北': ['河北', '石家庄', 'hebei', 'shijiazhuang'],
            '山西': ['山西', '太原', '吕梁', 'shanxi', 'taiyuan', 'lvliang'],
            '内蒙古': ['内蒙古', '呼和浩特', 'neimenggu', 'hohhot'],
            '新疆': ['新疆', '乌鲁木齐', 'xinjiang', 'wulumuqi'],
            '西藏': ['西藏', '拉萨', 'xizang', 'tibet', 'lhasa'],
            '云南': ['云南', '昆明', 'yunnan', 'kunming'],
            '贵州': ['贵州', '贵阳', 'guizhou', 'guiyang'],
            '甘肃': ['甘肃', '兰州', 'gansu', 'lanzhou'],
            '青海': ['青海', '西宁', 'qinghai', 'xining'],
            '宁夏': ['宁夏', '银川', 'ningxia', 'yinchuan'],
            '广西': ['广西', '南宁', 'guangxi', 'nanning'],
            '海南': ['海南', '海口', '三亚', 'hainan', 'haikou', 'sanya'],
            '香港': ['香港', 'hongkong', '港'],
            '澳门': ['澳门', 'macau', 'macao'],
            '台湾': ['台湾', '台', 'taiwan']
        }

        # 检查每个地区的关键词
        for region, keywords in regions.items():
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    return region

        # 默认返回"国内"
        return '国内'

    def _get_source_weight(self, source):
        """根据新闻来源确定权重"""
        source_lower = source.lower()

        # 主要国际新闻源权重较高
        if 'bbc' in source_lower or 'reuters' in source_lower or 'ap' in source_lower:
            return 30
        elif 'npr' in source_lower:
            return 25
        elif 'cnn' in source_lower or 'fox' in source_lower or 'bloomberg' in source_lower:
            return 20
        elif 'guardian' in source_lower or 'independent' in source_lower:
            return 18
        else:
            # 其他新闻源
            return 15

    def _calculate_quality_score(self, title, source, pub_date, region):
        """计算新闻质量评分 (0-100)"""
        score = 70  # 基础分数

        # 根据来源权重调整
        source_weight = self._get_source_weight(source)
        score += (source_weight - 15) * 0.5  # 来源权重贡献

        # 标题质量评估
        title_length = len(title)
        if title_length > 30 and title_length < 100:
            score += 5  # 适中长度标题更好
        elif title_length >= 100:
            score -= 5   # 过长标题可读性差

        # 检查标题是否完整（包含主要信息）
        if '?' not in title and '...' not in title:
            score += 5

        # 根据地区调整（某些地区新闻可能质量更高）
        if region == '北美' or region == '欧洲':
            score += 3
        elif region == '全球':
            score += 2

        # 发布时间影响（如果新闻是最近的）
        # 这里简单判断，实际可以解析pub_date
        if '2026' in pub_date:
            score += 5

        # 确保分数在合理范围内
        score = max(60, min(score, 95))

        return int(score)

    def _calculate_international_hot_score(self, pub_date, quality_score, region):
        """计算国际新闻热度分数"""
        score = 500  # 基础热度分数

        # 基于发布时间的新鲜度
        import re
        from datetime import datetime, timezone

        # 尝试解析发布时间
        try:
            # 处理常见的时间格式
            if re.search(r'\d{4}-\d{2}-\d{2}', pub_date):
                # 类似 "2026-04-14 16:34:06" 格式
                dt = datetime.strptime(pub_date.split()[0], '%Y-%m-%d')
            elif re.search(r'\w{3}, \d{2} \w{3} \d{4}', pub_date):
                # 类似 "Tue, 14 Apr 2026 16:34:06 -0400" 格式
                dt = datetime.strptime(pub_date[:16], '%a, %d %b %Y')
            else:
                # 默认使用当前时间
                dt = datetime.now()
        except Exception:
            dt = datetime.now()

        # 计算时间差（小时）
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        time_diff_hours = (now - dt).total_seconds() / 3600

        # 时间越近，热度越高
        if time_diff_hours < 24:
            score += 300  # 24小时内的新闻
        elif time_diff_hours < 72:
            score += 200  # 3天内的新闻
        elif time_diff_hours < 168:
            score += 100  # 一周内的新闻

        # 质量评分贡献
        score += quality_score * 3

        # 地区热度调整（某些地区新闻更受关注）
        if region == '中东' or region == '北美':
            score += 50
        elif region == '欧洲':
            score += 40
        elif region == '亚洲':
            score += 30

        return int(score)

    # ==================== 搜索功能增强 ====================

    def search_news(self, keyword: str = '', category: str = 'all', fulltext: bool = True,
                    time_range: str = 'all', source: str = '',
                    sentiment: str = 'all', max_results: int = 50) -> list:
        """
        全文搜索新闻（标题+内容），支持高级筛选

        Args:
            keyword: 搜索关键词（为空则返回所有）
            category: 'domestic' / 'international' / 'all'
            fulltext: 是否搜索内容（否则仅搜索标题）
            time_range: '24h' / '3d' / '7d' / '30d' / 'all'
            source: 来源筛选（为空不过滤）
            sentiment: 'positive' / 'negative' / 'neutral' / 'all'
            max_results: 最大返回数量

        Returns:
            匹配的新闻列表
        """
        from datetime import datetime, timedelta, timezone

        news_data = self.get_hot_news()
        results = []

        # 收集新闻
        if category in ('domestic', 'all'):
            for item in news_data.get('domestic', []):
                item['_category'] = 'domestic'
                results.append(item)
        if category in ('international', 'all'):
            for item in news_data.get('international', []):
                item['_category'] = 'international'
                results.append(item)

        # 关键词过滤
        if keyword:
            kw = keyword.lower().strip()
            filtered = []
            for item in results:
                title = (item.get('title') or '').lower()
                content = (item.get('content') or item.get('description') or '').lower()
                source_text = (item.get('source') or '').lower()
                region = (item.get('region') or '').lower()

                match = False
                # 标题匹配
                if kw in title:
                    match = True
                # 来源匹配
                if kw in source_text:
                    match = True
                # 地区匹配
                if kw in region:
                    match = True
                # 内容匹配（全文搜索）
                if fulltext and kw in content:
                    match = True

                if match:
                    filtered.append(item)
            results = filtered

        # 时间范围筛选
        if time_range != 'all':
            now = datetime.now(timezone.utc)
            time_map = {
                '24h': timedelta(hours=24),
                '3d': timedelta(days=3),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }
            delta = time_map.get(time_range)
            if delta:
                cutoff = now - delta
                time_filtered = []
                for item in results:
                    pub_date = item.get('published', '')
                    if pub_date:
                        try:
                            # 尝试多种日期格式
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%a, %d %b %Y %H:%M:%S %z',
                                        '%Y-%m-%d', '%a, %d %b %Y']:
                                try:
                                    dt = datetime.strptime(pub_date, fmt)
                                    if dt.tzinfo is None:
                                        dt = dt.replace(tzinfo=timezone.utc)
                                    if dt >= cutoff:
                                        time_filtered.append(item)
                                    break
                                except ValueError:
                                    continue
                            else:
                                time_filtered.append(item)
                        except Exception:
                            time_filtered.append(item)
                    else:
                        time_filtered.append(item)
                results = time_filtered

        # 来源筛选
        if source:
            source_lower = source.lower().strip()
            results = [item for item in results
                       if source_lower in (item.get('source') or '').lower()]

        # 情感筛选（需要调用情感分析 - 仅对少量结果分析以避免性能开销）
        if sentiment != 'all' and results:
            from sentiment_analyzer import get_sentiment_analyzer
            analyzer = get_sentiment_analyzer()
            sentiment_filtered = []
            for item in results[:30]:  # 最多分析30条以保持性能
                title = item.get('title', '')
                content = item.get('content') or item.get('description') or title
                try:
                    result = analyzer.analyze_sentiment(content, title)
                    item['_sentiment'] = result.get('sentiment', 'neutral')
                    item['_sentiment_label'] = result.get('sentiment_label', '中性')
                    item['_sentiment_score'] = result.get('score', 0)
                    if result.get('sentiment') == sentiment:
                        sentiment_filtered.append(item)
                except Exception:
                    sentiment_filtered.append(item)
            results = sentiment_filtered

        # 按热度排序
        results.sort(key=lambda x: x.get('hot_score', 0) or 0, reverse=True)

        return results[:max_results]

    def get_all_sources(self) -> list:
        """获取所有新闻来源列表"""
        news_data = self.get_hot_news()
        sources = set()
        for category in ['domestic', 'international']:
            for item in news_data.get(category, []):
                source = item.get('source', '')
                if source:
                    sources.add(source)
        return sorted(sources)

    def get_hot_news(self):
        domestic = []
        international = []

        try:
            toutiao_data = self._fetch_json(self.DOMESTIC_TOUTIAO_URL)
            domestic = self._parse_toutiao_hot(toutiao_data, max_items=10)
        except (requests.RequestException, ValueError):
            domestic = []

        try:
            weibo_xml = self._fetch_feed(self.DOMESTIC_WEIBO_URL)
            weibo_news = self._parse_rss(weibo_xml, max_items=10)
            for item in weibo_news:
                item['link'] = 'https://weibo.com/'
            domestic.extend(weibo_news)
        except requests.RequestException:
            pass

        try:
            international_xml = self._fetch_feed(self.INTERNATIONAL_FEED_URL)
            international = self._parse_rss(international_xml, max_items=10)
        except requests.RequestException:
            international = []

        return {
            'domestic': domestic,
            'international': international,
        }
