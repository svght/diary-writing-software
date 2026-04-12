import requests
import json

class LocationService:
    """地理位置服务类，用于获取和解析地理位置信息"""
    
    def __init__(self):
        """初始化地理位置服务"""
        pass
        
    def get_location_by_ip(self):
        """
        通过IP地址自动获取当前位置信息
        
        Returns:
            dict: 包含位置信息的字典，如果失败返回None
        """
        try:
            # 使用 ip-api.com 免费服务
            response = requests.get('http://ip-api.com/json/', timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'success':
                location_info = {
                    'city': data.get('city', ''),
                    'region': data.get('regionName', ''),
                    'country': data.get('country', ''),
                    'country_code': data.get('countryCode', ''),
                    'latitude': data.get('lat', 0),
                    'longitude': data.get('lon', 0),
                    'timezone': data.get('timezone', ''),
                    'isp': data.get('isp', ''),
                    'query': data.get('query', '')
                }
                return location_info
            else:
                print(f"获取位置失败: {data.get('message', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"解析位置数据失败: {e}")
            return None
    
    def get_city_by_ip(self):
        """
        通过IP地址获取当前城市名称
        
        Returns:
            str: 城市名称，如果失败返回空字符串
        """
        location = self.get_location_by_ip()
        if location and location['city']:
            return location['city']
        return ""
    
    def get_coordinates_by_city(self, city_name):
        """
        通过城市名称获取经纬度坐标
        
        Args:
            city_name (str): 城市名称（如"Beijing, China"）
            
        Returns:
            tuple: (latitude, longitude) 或 (None, None) 如果失败
        """
        try:
            from geopy.geocoders import Nominatim
            from geopy.exc import GeocoderTimedOut, GeocoderServiceError
            geolocator = Nominatim(user_agent="diary_app")
            location = geolocator.geocode(city_name, timeout=10)
            if location:
                return (location.latitude, location.longitude)
            return (None, None)
        except (ImportError, GeocoderTimedOut, GeocoderServiceError, Exception) as e:
            print(f"地理编码失败: {e}")
            return (None, None)

    def get_city_by_coordinates(self, latitude, longitude):
        """
        通过经纬度坐标获取城市名称
        
        Args:
            latitude (float): 纬度
            longitude (float): 经度
            
        Returns:
            str: 城市名称，如果失败返回空字符串
        """
        try:
            url = 'https://api.bigdatacloud.net/data/reverse-geocode-client'
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'localityLanguage': 'zh',
            }
            headers = {
                'User-Agent': 'diary_app/1.0'
            }
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            city = data.get('city') or data.get('locality') or data.get('principalSubdivision') or data.get('countryName')
            return city or ""
        except requests.exceptions.RequestException as e:
            print(f"反向地理编码请求失败: {e}")
            return ""
        except (KeyError, ValueError) as e:
            print(f"反向地理编码解析失败: {e}")
            return ""
    
    def get_formatted_location(self):
        """
        获取格式化的位置信息字符串
        
        Returns:
            str: 格式化后的位置信息字符串
        """
        location = self.get_location_by_ip()
        if not location:
            return "无法获取位置信息"
        
        parts = []
        if location['city']:
            parts.append(location['city'])
        if location['region']:
            parts.append(location['region'])
        if location['country']:
            parts.append(location['country'])
        
        return "，".join(parts)
    
    def validate_city_name(self, city_name):
        """
        验证城市名称是否有效
        
        Args:
            city_name (str): 城市名称
            
        Returns:
            bool: 城市名称是否有效
        """
        lat, lon = self.get_coordinates_by_city(city_name)
        return lat is not None and lon is not None

# 预定义的中国主要城市列表
CHINESE_CITIES = [
    "北京", "上海", "广州", "深圳", "天津", "重庆", "成都", "武汉", "西安", 
    "南京", "杭州", "苏州", "青岛", "大连", "沈阳", "长春", "哈尔滨", 
    "石家庄", "太原", "济南", "合肥", "南昌", "福州", "厦门", "长沙", 
    "郑州", "昆明", "贵阳", "南宁", "海口", "兰州", "西宁", "银川", "乌鲁木齐"
]