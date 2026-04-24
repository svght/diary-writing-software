#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek新闻评论与改写生成器 - 智能新闻工作台
实现多类型新闻评论生成和新闻改写功能：
1. DeepSeek API集成
2. 多类型新闻评论生成（8种评论类型）
3. 批量评论生成
4. 新闻多风格改写功能（8种改写风格）
5. 评论缓存和存储
6. 使用量统计和限制
7. 改写结果保存
"""

import os
import json
import re
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import requests
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


@dataclass
class GenerationResult:
    """生成结果数据类"""
    success: bool
    comment: str = ""
    rewritten_text: str = ""
    error: str = ""
    model: str = ""
    usage_tokens: Dict[str, int] = None
    generation_time: float = 0.0
    cached: bool = False
    news_id: str = ""
    news_title: str = ""
    generation_type: str = "comment"  # comment 或 rewrite
    comment_type: str = ""  # 评论类型（如 insightful, critical 等）
    rewrite_style: str = ""  # 改写风格（如 formal, casual 等）


@dataclass
class UsageStats:
    """使用量统计"""
    total_tokens: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_reset_time: datetime = None
    daily_limit: int = 10000
    request_limit: int = 100

    def __post_init__(self):
        if self.last_reset_time is None:
            self.last_reset_time = datetime.now()


class DeepSeekCommentGenerator:
    """DeepSeek评论与改写生成器"""

    MODELS = {
        "deepseek-chat": "deepseek-chat",
        "deepseek-reasoner": "deepseek-reasoner"
    }

    # 8种评论类型
    COMMENT_TYPES = {
        "insightful": {
            "label": "深度分析型",
            "system_prompt": """你是一个资深的新闻评论员，擅长深度分析新闻事件。
请遵守以下规则：
1. 评论长度在150-300字之间
2. 深入分析新闻的背景、影响和未来趋势
3. 提供独特的洞察和观点
4. 结合相关领域知识进行解读
5. 语言专业、有说服力
6. 避免空洞的套话""",
            "user_prompt": "请为以下新闻生成一篇深度分析型评论，挖掘事件背后的深层含义和影响：\n\n"
        },
        "critical": {
            "label": "批判质疑型",
            "system_prompt": """你是一个具有批判精神的评论家，善于发现问题和提出质疑。
请遵守以下规则：
1. 评论长度在100-250字之间
2. 理性指出新闻中可能存在的问题或争议点
3. 提出建设性的质疑和思考
4. 保持客观理性，避免情绪化攻击
5. 可以提出不同角度的看法
6. 基于事实进行批评""",
            "user_prompt": "请为以下新闻生成一篇批判质疑型评论，理性分析其中可能存在的问题：\n\n"
        },
        "supportive": {
            "label": "支持赞同型",
            "system_prompt": """你是一个积极正面的评论者，善于发现新闻中的亮点和价值。
请遵守以下规则：
1. 评论长度在100-200字之间
2. 表达对新闻事件或决策的支持和理解
3. 肯定新闻中的积极意义和价值
4. 语言温暖、有建设性
5. 可以适当展望积极前景
6. 保持真诚，避免过度吹捧""",
            "user_prompt": "请为以下新闻生成一篇支持赞同型评论，表达对其中积极意义的认可：\n\n"
        },
        "humorous": {
            "label": "幽默调侃型",
            "system_prompt": """你是一个风趣幽默的评论者，善于用轻松幽默的方式评论新闻。
请遵守以下规则：
1. 评论长度在80-180字之间
2. 运用幽默、调侃、双关等手法
3. 保持风趣但不低俗
4. 不要拿严肃话题（灾难、悲剧等）开玩笑
5. 让读者会心一笑的同时有所思考
6. 语气轻松活泼""",
            "user_prompt": "请为以下新闻生成一篇幽默调侃型评论，用轻松风趣的方式点评：\n\n"
        },
        "professional": {
            "label": "专业分析型",
            "system_prompt": """你是一个行业专家，擅长从专业角度分析新闻事件。
请遵守以下规则：
1. 评论长度在200-400字之间
2. 运用专业术语和行业知识进行分析
3. 提供深度的行业洞察和判断
4. 引用相关数据或案例支持观点
5. 对事件的影响和趋势做出专业判断
6. 语言严谨、专业""",
            "user_prompt": "请从专业角度对以下新闻进行分析，提供行业级的深度解读：\n\n"
        },
        "emotional": {
            "label": "情感共鸣型",
            "system_prompt": """你是一个富有同理心的评论者，擅长引起读者的情感共鸣。
请遵守以下规则：
1. 评论长度在120-250字之间
2. 从人文关怀的角度出发
3. 表达对事件中人物的共情和理解
4. 语言温暖、感人
5. 引发读者情感共鸣
6. 保持真诚，避免煽情过度""",
            "user_prompt": "请为以下新闻生成一篇情感共鸣型评论，从人文关怀的角度表达感受：\n\n"
        },
        "short": {
            "label": "短评快评型",
            "system_prompt": """你是一个犀利的快评高手，用最精炼的语言表达观点。
请遵守以下规则：
1. 评论长度控制在30-80字之间
2. 一针见血，直击要点
3. 语言精炼有力
4. 可以是一句话点评
5. 适合快速阅读和传播
6. 观点鲜明，不拖泥带水""",
            "user_prompt": "请为以下新闻生成一篇短小精悍的快评，一句话直击要害：\n\n"
        },
        "balanced": {
            "label": "中立平衡型",
            "system_prompt": """你是一个客观中立的评论者，善于平衡各方观点。
请遵守以下规则：
1. 评论长度在150-300字之间
2. 全面呈现事件的多方面影响
3. 平衡正反两面观点
4. 保持客观中立的态度
5. 为读者提供全面的思考视角
6. 避免偏颇和极端言论""",
            "user_prompt": "请为以下新闻生成一篇中立平衡型评论，客观全面地分析利弊：\n\n"
        }
    }

    # 8种改写风格
    REWRITE_STYLES = {
        "formal": {
            "label": "正式官方",
            "prompt": "请以正式、官方的新闻风格改写以下内容，使用规范的书面语，语气庄重严谨，适合官方媒体发布。"
        },
        "casual": {
            "label": "轻松口语",
            "prompt": "请以轻松、口语化的风格改写以下内容，像朋友间聊天一样自然亲切，适合社交媒体发布。"
        },
        "concise": {
            "label": "简洁精炼",
            "prompt": "请以简洁、精炼的风格改写以下内容，删除冗余信息，保留核心要点，适合快速阅读。"
        },
        "detailed": {
            "label": "详细深入",
            "prompt": "请以详细、深入的风格改写以下内容，补充背景信息和细节分析，适合深度阅读。"
        },
        "headline": {
            "label": "标题党风格",
            "prompt": "请以吸引眼球的标题党风格改写以下内容，使用有冲击力的表达方式，让人忍不住想点击阅读。"
        },
        "storytelling": {
            "label": "故事叙述",
            "prompt": "请以故事叙述的风格改写以下内容，采用故事化的结构和语言，有情节有细节，引人入胜。"
        },
        "analytical": {
            "label": "分析评论",
            "prompt": "请以分析评论的风格改写以下内容，结合评论和分析，不仅有事实陈述还有观点解读。"
        },
        "summary": {
            "label": "摘要简报",
            "prompt": "请以摘要简报的风格改写以下内容，提取最核心的信息，用要点式或简报形式呈现。"
        }
    }

    def __init__(self, api_key: str = None, model: str = "deepseek-chat"):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未提供，请设置DEEPSEEK_API_KEY环境变量或传入api_key参数")

        self.model = model if model in self.MODELS else "deepseek-chat"
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.cache_dir = "comments_cache"
        self.usage_stats = UsageStats()
        self.rewrite_save_dir = "saved_rewrites"

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        if not os.path.exists(self.rewrite_save_dir):
            os.makedirs(self.rewrite_save_dir)

        self._load_usage_stats()

    def _get_cache_path(self, content_hash: str) -> str:
        return os.path.join(self.cache_dir, f"{content_hash}.json")

    def _create_content_hash(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _load_from_cache(self, content_hash: str) -> Optional[Dict[str, Any]]:
        cache_path = self._get_cache_path(content_hash)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None

    def _save_to_cache(self, content_hash: str, data: Dict[str, Any]):
        cache_path = self._get_cache_path(content_hash)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _load_usage_stats(self):
        stats_path = os.path.join(self.cache_dir, "usage_stats.json")
        if os.path.exists(stats_path):
            try:
                with open(stats_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_reset_str = data.get('last_reset_time')
                    if last_reset_str:
                        last_reset = datetime.fromisoformat(last_reset_str)
                        if datetime.now() - last_reset > timedelta(days=1):
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
        stats_path = os.path.join(self.cache_dir, "usage_stats.json")
        try:
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.usage_stats), f, ensure_ascii=False, indent=2)
        except:
            pass

    def _update_usage_stats(self, tokens_used: int, success: bool = True):
        self.usage_stats.total_tokens += tokens_used
        self.usage_stats.total_requests += 1
        if success:
            self.usage_stats.successful_requests += 1
        else:
            self.usage_stats.failed_requests += 1
        self._save_usage_stats()

    def check_usage_limits(self) -> Tuple[bool, str]:
        if self.usage_stats.total_tokens >= self.usage_stats.daily_limit:
            return False, f"已达到每日token使用限制：{self.usage_stats.total_tokens}/{self.usage_stats.daily_limit}"
        if self.usage_stats.total_requests >= self.usage_stats.request_limit:
            return False, f"已达到每日请求次数限制：{self.usage_stats.total_requests}/{self.usage_stats.request_limit}"
        return True, ""

    @staticmethod
    def _remove_lone_surrogates(text: str) -> str:
        """
        移除或替换可能导致JSON解析错误的单独代理项（lone surrogate characters）。
        
        Unicode代理项（U+D800-U+DFFF）是UTF-16编码中的特殊字符，
        单个出现时会导致JSON序列化/反序列化错误（如"lone leading surrogate in hex escape"）。
        
        Args:
            text: 输入文本
            
        Returns:
            清理后的文本（lone surrogate被移除）
        """
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        # 匹配高代理项（U+D800-U+DBFF）后没有紧跟低代理项（U+DC00-U+DFFF）的孤立高代理项
        text = re.sub(r'[\uD800-\uDBFF](?![\uDC00-\uDFFF])', '', text)
        # 匹配低代理项（U+DC00-U+DFFF）前面没有高代理项（U+D800-U+DBFF）的孤立低代理项
        text = re.sub(r'(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]', '', text)
        return text

    def _call_api(self, messages: list, max_tokens: int = 500, temperature: float = 0.7) -> Tuple[bool, Dict, str]:
        """调用DeepSeek API的通用方法"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 清理消息内容，移除可能导致JSON解析错误的特殊字符
        cleaned_messages = []
        for msg in messages:
            if isinstance(msg, dict) and 'content' in msg:
                content = msg['content']
                # 确保内容是字符串
                if not isinstance(content, str):
                    content = str(content)
                # 第一步：移除单独代理项（lone surrogate）
                content = self._remove_lone_surrogates(content)
                # 第二步：移除可能导致JSON解析错误的控制字符（保留换行符和制表符）
                content = ''.join(char for char in content if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) != 127))
                cleaned_messages.append({
                    "role": msg.get("role", "user"),
                    "content": content
                })
            else:
                cleaned_messages.append(msg)

        # 根据模型类型构建不同的payload
        # deepseek-reasoner 是推理模型，有特殊要求：
        #   - 不支持 temperature 和 top_p 参数
        #   - 应使用 max_completion_tokens 而非 max_tokens
        #   - API 响应中可能包含 reasoning_content 字段（思考过程），需忽略
        if self.model == "deepseek-reasoner":
            payload = {
                "model": self.model,
                "messages": cleaned_messages,
                "max_completion_tokens": max_tokens,
                "stream": False
            }
        else:
            payload = {
                "model": self.model,
                "messages": cleaned_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "stream": False
            }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            # 对于 deepseek-reasoner，响应中可能包含 reasoning_content 字段
            # 我们只提取 content，忽略 reasoning_content（思考过程）
            content = message.get("content", "").strip()
            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            return True, {"content": content, "usage": usage, "tokens_used": tokens_used}, ""
        except requests.exceptions.RequestException as e:
            return False, {}, f"API请求失败：{str(e)}"
        except (KeyError, IndexError) as e:
            return False, {}, f"API响应解析失败：{str(e)}"
        except json.JSONDecodeError as e:
            return False, {}, f"JSON解析错误：{str(e)}"
        except Exception as e:
            return False, {}, f"未知错误：{str(e)}"

    def generate_comment_for_news(self, news_title: str, news_content: str = "",
                                  news_id: str = "", comment_type: str = "insightful") -> GenerationResult:
        """
        为新闻生成指定类型的评论

        Args:
            news_title: 新闻标题
            news_content: 新闻内容
            news_id: 新闻ID
            comment_type: 评论类型，可选值：
                insightful(深度分析), critical(批判质疑), supportive(支持赞同),
                humorous(幽默调侃), professional(专业分析), emotional(情感共鸣),
                short(短评快评), balanced(中立平衡)

        Returns:
            GenerationResult
        """
        start_time = time.time()

        # 获取评论类型配置
        comment_config = self.COMMENT_TYPES.get(comment_type)
        if not comment_config:
            comment_config = self.COMMENT_TYPES["insightful"]
            comment_type = "insightful"

        # 缓存key包含评论类型
        content_to_hash = f"{comment_type}:{news_title}:{news_content}"
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
                news_title=news_title,
                comment_type=comment_type,
                generation_type="comment"
            )

        # 检查使用限制
        can_generate, error_msg = self.check_usage_limits()
        if not can_generate:
            return GenerationResult(
                success=False, error=error_msg, news_id=news_id, news_title=news_title,
                comment_type=comment_type, generation_type="comment"
            )

        # 构建消息
        messages = [
            {"role": "system", "content": comment_config["system_prompt"]},
            {
                "role": "user",
                "content": f"""{comment_config['user_prompt']}
新闻标题：{news_title}

{('新闻内容：' + news_content) if news_content else '请根据标题生成评论'}

请生成评论："""
            }
        ]

        # 调用API
        success, result, error_msg = self._call_api(messages, max_tokens=600, temperature=0.7)

        if success:
            comment = result["content"]
            usage = result["usage"]
            tokens_used = result["tokens_used"]

            self._update_usage_stats(tokens_used, success=True)

            # 缓存
            cache_data = {
                "comment": comment,
                "model": self.model,
                "usage_tokens": usage,
                "generated_at": datetime.now().isoformat(),
                "news_title": news_title,
                "news_content": news_content,
                "news_id": news_id,
                "comment_type": comment_type
            }
            self._save_to_cache(content_hash, cache_data)

            return GenerationResult(
                success=True, comment=comment, model=self.model,
                usage_tokens=usage, generation_time=time.time() - start_time,
                cached=False, news_id=news_id, news_title=news_title,
                comment_type=comment_type, generation_type="comment"
            )
        else:
            self._update_usage_stats(0, success=False)
            return GenerationResult(
                success=False, error=error_msg, generation_time=time.time() - start_time,
                news_id=news_id, news_title=news_title,
                comment_type=comment_type, generation_type="comment"
            )

    def generate_comments_batch(self, news_items: List[Dict[str, str]],
                                max_concurrent: int = 3,
                                comment_type: str = "insightful") -> List[GenerationResult]:
        """批量生成评论（支持指定评论类型）"""
        results = []
        for i, news_item in enumerate(news_items):
            title = news_item.get("title", "")
            content = news_item.get("content", "")
            news_id = news_item.get("id", f"news_{i}")
            result = self.generate_comment_for_news(title, content, news_id, comment_type)
            results.append(result)
            if i < len(news_items) - 1:
                time.sleep(0.5)
        return results

    def rewrite_news(self, news_title: str, news_content: str,
                     style: str = "formal") -> GenerationResult:
        """
        改写新闻

        Args:
            news_title: 新闻标题
            news_content: 新闻内容
            style: 改写风格，可选值：
                formal(正式官方), casual(轻松口语), concise(简洁精炼),
                detailed(详细深入), headline(标题党), storytelling(故事叙述),
                analytical(分析评论), summary(摘要简报)

        Returns:
            GenerationResult
        """
        start_time = time.time()

        # 获取改写风格配置
        style_config = self.REWRITE_STYLES.get(style)
        if not style_config:
            style_config = self.REWRITE_STYLES["formal"]
            style = "formal"

        style_prompt = style_config["prompt"]

        # 检查使用限制
        can_generate, error_msg = self.check_usage_limits()
        if not can_generate:
            return GenerationResult(
                success=False, error=error_msg, news_id="", news_title=news_title,
                rewrite_style=style, generation_type="rewrite"
            )

        # 构建消息
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的新闻编辑，擅长用不同风格改写新闻内容。
请遵守以下规则：
1. 保留新闻的核心事实和关键信息
2. 根据要求的风格调整语言表达方式
3. 确保改写后的内容通顺、自然
4. 保持新闻的准确性和可信度
5. 不要添加原文中没有的事实信息
6. 改写后的标题要匹配相应的风格"""
            },
            {
                "role": "user",
                "content": f"""{style_prompt}

新闻标题：{news_title}

新闻内容：{news_content}

请生成改写后的完整新闻（包括标题和正文）："""
            }
        ]

        # 调用API
        temperature = 0.5 if style in ["formal", "concise", "summary"] else 0.7
        max_tokens = 1200
        if style == "detailed":
            max_tokens = 1500
        elif style == "summary":
            max_tokens = 500

        success, result, error_msg = self._call_api(messages, max_tokens=max_tokens, temperature=temperature)

        if success:
            rewritten_text = result["content"]
            usage = result["usage"]
            tokens_used = result["tokens_used"]

            self._update_usage_stats(tokens_used, success=True)

            return GenerationResult(
                success=True, rewritten_text=rewritten_text, model=self.model,
                usage_tokens=usage, generation_time=time.time() - start_time,
                cached=False, news_id="", news_title=news_title,
                rewrite_style=style, generation_type="rewrite"
            )
        else:
            self._update_usage_stats(0, success=False)
            return GenerationResult(
                success=False, error=error_msg, generation_time=time.time() - start_time,
                news_id="", news_title=news_title,
                rewrite_style=style, generation_type="rewrite"
            )

    def save_rewrite_result(self, news_title: str, original_content: str,
                            rewritten_text: str, style: str) -> Dict[str, str]:
        """
        保存改写结果到本地文件

        Returns:
            Dict with file paths: {json_path, txt_path}
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in news_title)[:50]
        base_name = f"rewrite_{safe_title}_{style}_{timestamp}"

        json_path = os.path.join(self.rewrite_save_dir, f"{base_name}.json")
        txt_path = os.path.join(self.rewrite_save_dir, f"{base_name}.txt")

        # 保存JSON
        data = {
            "news_title": news_title,
            "original_content": original_content,
            "rewritten_text": rewritten_text,
            "style": style,
            "style_label": self.REWRITE_STYLES.get(style, {}).get("label", style),
            "saved_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "model": self.model
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 保存TXT
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 56 + "\n")
            f.write(f"智能新闻工作台 - 改写结果\n")
            f.write("=" * 56 + "\n")
            f.write(f"原标题: {news_title}\n")
            f.write(f"改写风格: {self.REWRITE_STYLES.get(style, {}).get('label', style)}\n")
            f.write(f"保存时间: {data['saved_at']}\n")
            f.write(f"模型: {self.model}\n")
            f.write("\n--- 原文 ---\n\n")
            f.write(original_content)
            f.write("\n\n--- 改写结果 ---\n\n")
            f.write(rewritten_text)
            f.write("\n\n" + "=" * 56 + "\n")

        return {"json_path": json_path, "txt_path": txt_path}

    def get_usage_info(self) -> Dict[str, Any]:
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

    def get_comment_types_info(self) -> List[Dict[str, str]]:
        """获取所有评论类型信息"""
        return [
            {"key": key, "label": config["label"]}
            for key, config in self.COMMENT_TYPES.items()
        ]

    def get_rewrite_styles_info(self) -> List[Dict[str, str]]:
        """获取所有改写风格信息"""
        return [
            {"key": key, "label": config["label"]}
            for key, config in self.REWRITE_STYLES.items()
        ]

    def clear_cache(self):
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir)

    def reset_usage_stats(self):
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
            class MockGenerator:
                def __init__(self):
                    self.model = "mock-model"
                    self.usage_stats = UsageStats()
                    self.rewrite_save_dir = "saved_rewrites"
                    self.COMMENT_TYPES = DeepSeekCommentGenerator.COMMENT_TYPES
                    self.REWRITE_STYLES = DeepSeekCommentGenerator.REWRITE_STYLES

                def generate_comment_for_news(self, news_title, news_content="", news_id="", comment_type="insightful"):
                    type_label = self.COMMENT_TYPES.get(comment_type, {}).get("label", comment_type)
                    return GenerationResult(
                        success=True,
                        comment=f"【{type_label}评论】这是为新闻'{news_title}'生成的模拟{type_label}评论。请配置DeepSeek API密钥以使用真实生成功能。",
                        model="mock-model",
                        usage_tokens={"total_tokens": 100},
                        generation_time=0.5,
                        cached=False,
                        news_id=news_id,
                        news_title=news_title,
                        comment_type=comment_type,
                        generation_type="comment"
                    )

                def generate_comments_batch(self, news_items, max_concurrent=3, comment_type="insightful"):
                    return [
                        self.generate_comment_for_news(
                            item.get("title", ""), item.get("content", ""),
                            item.get("id", f"news_{i}"), comment_type
                        )
                        for i, item in enumerate(news_items)
                    ]

                def rewrite_news(self, news_title, news_content, style="formal"):
                    style_label = self.REWRITE_STYLES.get(style, {}).get("label", style)
                    return GenerationResult(
                        success=True,
                        rewritten_text=f"【{style_label}改写】这是新闻'{news_title}'的模拟{style_label}改写结果。请配置DeepSeek API密钥以使用真实改写功能。\n\n原文：{news_content}",
                        model="mock-model",
                        usage_tokens={"total_tokens": 200},
                        generation_time=0.8,
                        cached=False,
                        news_id="",
                        news_title=news_title,
                        rewrite_style=style,
                        generation_type="rewrite"
                    )

                def save_rewrite_result(self, news_title, original_content, rewritten_text, style):
                    return {"json_path": "mock_path.json", "txt_path": "mock_path.txt"}

                def get_usage_info(self):
                    return {"total_tokens": 0, "total_requests": 0,
                            "daily_limit": 10000, "request_limit": 100,
                            "remaining_tokens": 10000, "remaining_requests": 100}

                def get_comment_types_info(self):
                    return DeepSeekCommentGenerator.get_comment_types_info(self)

                def get_rewrite_styles_info(self):
                    return DeepSeekCommentGenerator.get_rewrite_styles_info(self)

            _generator_instance = MockGenerator()

    return _generator_instance
