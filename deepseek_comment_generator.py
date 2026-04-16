#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek评论生成器 - 第四阶段优化迭代6
实现新闻评论生成功能：
1. DeepSeek API集成
2. 单条新闻评论生成
3. 批量评论生成
4. 评论缓存和存储
5. 使用量统计和限制
"""

import os
import json
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import requests
from dataclasses import dataclass, asdict


@dataclass
class GenerationResult:
    """生成结果数据类"""
    success: bool
    comment: str = ""
    error: str = ""
    model: str = ""
    usage_tokens: Dict[str, int] = None
    generation_time: float = 0.0
    cached: bool = False
    news_id: str = ""
    news_title: str = ""


@dataclass
class UsageStats:
    """使用量统计"""
    total_tokens: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_reset_time: datetime = None
    daily_limit: int = 10000  # 每日token限制
    request_limit: int = 100  # 每日请求次数限制
    
    def __post_init__(self):
        if self.last_reset_time is None:
            self.last_reset_time = datetime.now()


class DeepSeekCommentGenerator:
    """DeepSeek评论生成器"""
    
    # 支持的模型
    MODELS = {
        "deepseek-chat": "deepseek-chat",
        "deepseek-reasoner": "deepseek-reasoner"
    }
    
    def __init__(self, api_key: str = None, model: str = "deepseek-chat"):
        """
        初始化DeepSeek评论生成器
        
        Args:
            api_key: DeepSeek API密钥，如果为None则从环境变量获取
            model: 使用的模型名称
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未提供，请设置DEEPSEEK_API_KEY环境变量或传入api_key参数")
        
        self.model = model if model in self.MODELS else "deepseek-chat"
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.cache_dir = "comments_cache"
        self.usage_stats = UsageStats()
        
        # 创建缓存目录
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # 加载使用统计
        self._load_usage_stats()
    
    def _get_cache_path(self, content_hash: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{content_hash}.json")
    
    def _create_content_hash(self, text: str) -> str:
        """创建内容哈希值用于缓存"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _load_from_cache(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """从缓存加载数据"""
        cache_path = self._get_cache_path(content_hash)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def _save_to_cache(self, content_hash: str, data: Dict[str, Any]):
        """保存数据到缓存"""
        cache_path = self._get_cache_path(content_hash)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def _load_usage_stats(self):
        """加载使用统计"""
        stats_path = os.path.join(self.cache_dir, "usage_stats.json")
        if os.path.exists(stats_path):
            try:
                with open(stats_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 检查是否需要重置每日限制
                    last_reset_str = data.get('last_reset_time')
                    if last_reset_str:
                        last_reset = datetime.fromisoformat(last_reset_str)
                        if datetime.now() - last_reset > timedelta(days=1):
                            # 重置每日使用量
                            data['total_tokens'] = 0
                            data['total_requests'] = 0
                            data['successful_requests'] = 0
                            data['failed_requests'] = 0
                            data['last_reset_time'] = datetime.now().isoformat()
                    
                    self.usage_stats = UsageStats(
                        total_tokens=data.get('total_tokens', 0),
                        total_requests=data.get('total_requests', 0),
                        successful_requests=data.get('successful_requests', 0),
                        failed_requests=data.get('failed_requests', 0),
                        last_reset_time=datetime.fromisoformat(data.get('last_reset_time', datetime.now().isoformat())),
                        daily_limit=data.get('daily_limit', 10000),
                        request_limit=data.get('request_limit', 100)
                    )
            except:
                pass
    
    def _save_usage_stats(self):
        """保存使用统计"""
        stats_path = os.path.join(self.cache_dir, "usage_stats.json")
        try:
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.usage_stats), f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def _update_usage_stats(self, tokens_used: int, success: bool = True):
        """更新使用统计"""
        self.usage_stats.total_tokens += tokens_used
        self.usage_stats.total_requests += 1
        
        if success:
            self.usage_stats.successful_requests += 1
        else:
            self.usage_stats.failed_requests += 1
        
        self._save_usage_stats()
    
    def check_usage_limits(self) -> Tuple[bool, str]:
        """检查使用限制"""
        # 检查是否超过每日token限制
        if self.usage_stats.total_tokens >= self.usage_stats.daily_limit:
            return False, f"已达到每日token使用限制：{self.usage_stats.total_tokens}/{self.usage_stats.daily_limit}"
        
        # 检查是否超过每日请求次数限制
        if self.usage_stats.total_requests >= self.usage_stats.request_limit:
            return False, f"已达到每日请求次数限制：{self.usage_stats.total_requests}/{self.usage_stats.request_limit}"
        
        return True, ""
    
    def generate_comment_for_news(self, news_title: str, news_content: str = "", 
                                  news_id: str = "") -> GenerationResult:
        """
        为新闻生成评论
        
        Args:
            news_title: 新闻标题
            news_content: 新闻内容（可选）
            news_id: 新闻ID（可选，用于缓存）
        
        Returns:
            GenerationResult: 生成结果
        """
        start_time = time.time()
        
        # 创建内容哈希用于缓存
        content_to_hash = f"{news_title}{news_content}"
        content_hash = self._create_content_hash(content_to_hash)
        
        # 检查缓存
        cached_data = self._load_from_cache(content_hash)
        if cached_data:
            return GenerationResult(
                success=True,
                comment=cached_data.get("comment", ""),
                model=cached_data.get("model", ""),
                usage_tokens=cached_data.get("usage_tokens", {}),
                generation_time=time.time() - start_time,
                cached=True,
                news_id=news_id,
                news_title=news_title
            )
        
        # 检查使用限制
        can_generate, error_msg = self.check_usage_limits()
        if not can_generate:
            return GenerationResult(
                success=False,
                error=error_msg,
                news_id=news_id,
                news_title=news_title
            )
        
        # 构建请求消息
        messages = [
            {
                "role": "system",
                "content": """你是一个新闻评论专家，擅长为新闻生成 insightful、balanced、engaging 的评论。
请遵守以下规则：
1. 评论长度在100-200字之间
2. 观点要客观、中立、有深度
3. 可以分析新闻的影响、背景、意义
4. 使用中文进行评论
5. 避免敏感话题和政治立场
6. 评论要有建设性，避免负面情绪"""
            },
            {
                "role": "user",
                "content": f"""请为以下新闻生成一个高质量的评论：

新闻标题：{news_title}

{('新闻内容：' + news_content) if news_content else '请根据标题生成评论'}

请生成一个 insightful、balanced、engaging 的评论："""
            }
        ]
        
        # 调用DeepSeek API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 提取评论
            comment = data["choices"][0]["message"]["content"].strip()
            
            # 获取使用量信息
            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            
            # 更新使用统计
            self._update_usage_stats(tokens_used, success=True)
            
            # 保存到缓存
            cache_data = {
                "comment": comment,
                "model": self.model,
                "usage_tokens": usage,
                "generated_at": datetime.now().isoformat(),
                "news_title": news_title,
                "news_content": news_content,
                "news_id": news_id
            }
            self._save_to_cache(content_hash, cache_data)
            
            return GenerationResult(
                success=True,
                comment=comment,
                model=self.model,
                usage_tokens=usage,
                generation_time=time.time() - start_time,
                cached=False,
                news_id=news_id,
                news_title=news_title
            )
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API请求失败：{str(e)}"
            self._update_usage_stats(0, success=False)
        except (KeyError, IndexError) as e:
            error_msg = f"API响应解析失败：{str(e)}"
            self._update_usage_stats(0, success=False)
        except Exception as e:
            error_msg = f"未知错误：{str(e)}"
            self._update_usage_stats(0, success=False)
        
        return GenerationResult(
            success=False,
            error=error_msg,
            generation_time=time.time() - start_time,
            news_id=news_id,
            news_title=news_title
        )
    
    def generate_comments_batch(self, news_items: List[Dict[str, str]], 
                                max_concurrent: int = 3) -> List[GenerationResult]:
        """
        批量生成评论
        
        Args:
            news_items: 新闻列表，每个元素包含title、content、id等字段
            max_concurrent: 最大并发数
        
        Returns:
            List[GenerationResult]: 生成结果列表
        """
        results = []
        
        # 简单实现：顺序处理，后续可以优化为并发
        for i, news_item in enumerate(news_items):
            title = news_item.get("title", "")
            content = news_item.get("content", "")
            news_id = news_item.get("id", f"news_{i}")
            
            result = self.generate_comment_for_news(title, content, news_id)
            results.append(result)
            
            # 添加短暂延迟避免频率限制
            if i < len(news_items) - 1:
                time.sleep(0.5)
        
        return results
    
    def get_usage_info(self) -> Dict[str, Any]:
        """获取使用信息"""
        return {
            "total_tokens": self.usage_stats.total_tokens,
            "total_requests": self.usage_stats.total_requests,
            "successful_requests": self.usage_stats.successful_requests,
            "failed_requests": self.usage_stats.failed_requests,
            "daily_limit": self.usage_stats.daily_limit,
            "request_limit": self.usage_stats.request_limit,
            "remaining_tokens": max(0, self.usage_stats.daily_limit - self.usage_stats.total_tokens),
            "remaining_requests": max(0, self.usage_stats.request_limit - self.usage_stats.total_requests),
            "last_reset_time": self.usage_stats.last_reset_time.isoformat()
        }
    
    def clear_cache(self):
        """清空缓存"""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir)
    
    def reset_usage_stats(self):
        """重置使用统计"""
        self.usage_stats = UsageStats()
        self._save_usage_stats()


# 单例实例
_generator_instance = None

def get_deepseek_generator(api_key: str = None) -> DeepSeekCommentGenerator:
    """获取DeepSeek生成器单例实例"""
    global _generator_instance
    if _generator_instance is None:
        try:
            _generator_instance = DeepSeekCommentGenerator(api_key)
        except Exception as e:
            # 创建一个虚拟实例用于测试
            class MockGenerator:
                def __init__(self):
                    self.model = "mock-model"
                    self.usage_stats = UsageStats()
                
                def generate_comment_for_news(self, news_title, news_content="", news_id=""):
                    return GenerationResult(
                        success=True,
                        comment=f"这是为新闻 '{news_title}' 生成的模拟评论。请配置DeepSeek API密钥以使用真实生成功能。",
                        model="mock-model",
                        usage_tokens={"total_tokens": 100},
                        generation_time=0.5,
                        cached=False,
                        news_id=news_id,
                        news_title=news_title
                    )
                
                def generate_comments_batch(self, news_items, max_concurrent=3):
                    return [self.generate_comment_for_news(item.get("title", ""), 
                                                          item.get("content", ""),
                                                          item.get("id", f"news_{i}")) 
                            for i, item in enumerate(news_items)]
                
                def get_usage_info(self):
                    return {"total_tokens": 0, "total_requests": 0, 
                           "daily_limit": 10000, "request_limit": 100,
                           "remaining_tokens": 10000, "remaining_requests": 100}
            
            _generator_instance = MockGenerator()
    
    return _generator_instance