# 智能新闻工作台

一个基于 Flask 的本地浏览器应用，用于新闻采集、AI 多类型评论生成和 AI 多风格新闻改写。

## 功能概览

### 📡 新闻采集
- 实时获取国内外热点新闻
- 按地区/来源过滤新闻
- 新闻热度评分与排序
- 新闻地区分布可视化（Chart.js 图表）
- 新闻实体识别、摘要生成、情感分析

### 🤖 AI 多类型评论生成（8种）
利用 DeepSeek API 生成不同类型的新闻评论：
| 类型 | 说明 |
|------|------|
| 🔍 深度分析型 | 深入分析事件背景、影响和未来趋势 |
| ⚠️ 批判质疑型 | 理性指出问题，提出建设性质疑 |
| 👍 支持赞同型 | 发现新闻亮点，表达支持和理解 |
| 😄 幽默调侃型 | 轻松幽默的方式点评，风趣而不低俗 |
| 📊 专业分析型 | 从行业专家角度提供专业分析 |
| 💖 情感共鸣型 | 从人文关怀出发引起情感共鸣 |
| ⚡ 短评快评型 | 一句话精炼点评，直击要害 |
| ⚖️ 中立平衡型 | 客观全面呈现多方观点 |

### ✏️ AI 新闻改写编辑（8种风格）
利用 DeepSeek API 将新闻改写成不同风格：
| 风格 | 说明 |
|------|------|
| 📄 正式官方 | 规范书面语，适合官方媒体 |
| 💬 轻松口语 | 自然亲切，适合社交媒体 |
| 📝 简洁精炼 | 删除冗余，保留核心要点 |
| 📚 详细深入 | 补充背景，适合深度阅读 |
| 📰 标题党风格 | 冲击力表达，吸引点击 |
| 📖 故事叙述 | 故事化结构，引人入胜 |
| 📋 分析评论 | 结合事实与观点解读 |
| � 摘要简报 | 要点式简报形式呈现 |

### 🎨 界面特性
- 微软风格清爽界面
- 天气实时显示
- 原文与改写结果左右对比
- 改写结果可复制/保存到本地
- API 使用量实时统计

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥
**方法一：环境变量**
```bash
set DEEPSEEK_API_KEY=your_api_key_here
```

**方法二：代码中设置**
修改 `deepseek_comment_generator.py` 中 `DeepSeekCommentGenerator.__init__()` 的 `api_key` 参数。

### 3. 启动
```bash
python start.py
# 或直接运行
python main.py
```

浏览器会自动打开 http://127.0.0.1:5000

### 4. 使用说明

**生成评论：**
1. 新闻加载后，选择一条新闻
2. 选择评论类型（8种可选）
3. 点击"生成"按钮
4. 支持批量勾选新闻后点击"批量生成"

**改写新闻：**
1. 从下拉框选择新闻，或手动输入标题和内容
2. 选择改写风格（8种可选）
3. 点击"改写"按钮
4. 查看原文与改写结果的左右对比
5. 可复制改写结果或保存到本地文件

## 项目结构
```
├── main.py                          # Flask 主应用（路由定义）
├── start.py                         # 启动脚本
├── deepseek_comment_generator.py    # DeepSeek AI 评论/改写生成器
├── news_service.py                  # 新闻采集服务
├── news_analyzer.py                 # 新闻实体分析
├── news_summarizer.py               # 新闻摘要生成
├── sentiment_analyzer.py            # 情感分析
├── trend_analyzer.py                # 热度趋势分析
├── region_analyzer.py               # 地区分布分析
├── weather_service.py               # 天气服务
├── location_service.py              # 定位服务

├── requirements.txt                 # Python 依赖
├── templates/
│   └── index.html                   # 前端界面
├── static/
│   └── style.css                    # 样式文件
├── comments_cache/                  # 评论/改写缓存目录
├── saved_rewrites/                  # 改写结果保存目录

```

## 技术栈
- **后端**: Python Flask
- **AI 引擎**: DeepSeek API
- **前端**: HTML5 + CSS3 + JavaScript
- **图表**: Chart.js
- **数据**: 实时网络采集
