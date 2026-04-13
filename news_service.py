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

    def _fetch_feed(self, url):
        response = requests.get(url, headers=self.headers, timeout=8)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text

    def _fetch_json(self, url):
        response = requests.get(url, headers=self.headers, timeout=8)
        response.raise_for_status()
        return response.json()

    def _clean_text(self, value):
        if not value:
            return ''
        return ' '.join(str(value).split())

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
                    items.append({
                        'title': title,
                        'link': link,
                        'published': pub_date,
                        'source': source,
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
                items.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'source': source,
                })

        return items

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
