# 日记时间统计 Agent

一个从 HTML 日记中自动提取时间数据并生成可视化统计的工具。
<img width="2525" height="1258" alt="image" src="https://github.com/user-attachments/assets/c417e839-d88c-4bd4-86a4-05c8437d066e" />

## ⭐ 快速上手（5分钟）

### 第一步：克隆项目

打开命令行（CMD或PowerShell），运行：
```bash
git clone https://github.com/SPikerinbit/diary-manager.git
cd diary-manager
```

### 第二步：创建Python环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 第三步：配置API密钥

1. 打开 `config.yaml` 文件
2. 找到 `api_key` 这一行
3. 填入你的 DeepSeek 或 OpenAI API密钥

示例（使用 DeepSeek）：
```yaml
llm:
  provider: "openai"
  api_key: "sk-你的API密钥"        # 填入你的密钥
  base_url: "https://api.deepseek.com"
  model: "deepseek-chat"
```

获取 API 密钥：
- **DeepSeek**: https://platform.deepseek.com/
- **OpenAI**: https://platform.openai.com/

### 第四步：运行

```bash
run.bat
```

然后打开浏览器访问 http://127.0.0.1:5001 即可看到界面。

### 第五步：使用

1. 把写好的日记（支持 HTML、PDF、Word、Markdown）放入 `data/input` 文件夹
2. 再次双击 `run.bat`
3. 在浏览器中查看统计结果

---

## 功能特性

- 📄 **多格式支持** - HTML、PDF、Word、Markdown（未来可能支持OCR）
- 🤖 大模型自动提取时间数据（支持 DeepSeek、OpenAI 等）

- 🤖 大模型自动提取时间数据（支持 DeepSeek、OpenAI 等）
- 📊 Apple 风格 Web 仪表盘（环形图 + 分类树 + 诗词展示）
- 🌳 智能分类（自动发现新子分类）
- ⏰ 时间完整性校验（确保每天 24 小时）
- 📅 多维度统计（日/周/月/年）
- 🔄 自动文件监控

## 快速开始

### 环境要求

- Python 3.9+
- Windows

### 启动

双击 `run.bat` 即可自动：
1. 处理 `data/input` 中的新 HTML 日记
2. 打开 Web 界面 http://127.0.0.1:5001

### 使用

1. 将 HTML 日记文件放入 `data/input` 目录
2. 重新运行 `run.bat`
3. 在 Web 界面查看统计

### 日记格式要求

为了获得最佳效果，日记应包含：
- **明确的时间点**：如 "早上7点起床"、"下午3点学习"
- **具体活动内容**：如 "工作"、"学习数学"、"打游戏"
- **日期**：建议在日记第一行写明日期，如 "2026年3月16日"

日记示例：
```html
2026年3月16日 星期一
早上7点起床
7:30 吃早餐
8:00 通勤
9:00-12:00 工作
12:00 吃午饭
13:00-17:00 学习
18:00 吃晚饭
19:00 玩耍
22:00 睡觉
```

## 项目结构

```
diary-manager/
├── config.yaml          # 配置文件
├── run.py              # 入口文件
├── run.bat             # Windows 启动脚本
├── app/
│   ├── models.py        # 数据库模型
│   ├── processor.py    # 核心处理逻辑
│   ├── config.py       # 配置加载
│   ├── parser/         # 文档解析
│   │   └── html_parser.py
│   ├── llm/           # 大模型集成
│   │   ├── client.py
│   │   └── prompt.py
│   ├── routes/        # Web 路由
│   ├── watcher.py     # 文件监控
├── templates/          # HTML 模板
├── test/               # 测试脚本
└── data/               # 数据目录
    ├── input/          # 待处理文件
    └── processed/      # 已处理文件
```

## 配置说明

编辑 `config.yaml`：

```yaml
llm:
  provider: "openai"           # 或 anthropic
  api_key: "your-api-key"      # 必填
  base_url: "https://api.deepseek.com"  # DeepSeek API 地址
  model: "deepseek-chat"
  temperature: 0.0              # 温度设为0减少幻觉

app:
  host: "127.0.0.1"
  port: 5001

directories:
  input: "data/input"
  processed: "data/processed"
  database: "data/database.db"
```

## 数据处理流程

1. **第一阶段**：LLM 提取时间点序列
2. **第二阶段**：LLM 判断每个时间点具体做什么
3. **第三阶段**：自动归类到已有分类，或创建新子分类

### 分类体系

默认根分类：
- 工作
- 学习
- 睡觉
- 玩耍
- 吃饭
- 通勤
- 整理仪容仪表

子分类会根据日记内容自动创建，如：
- 工作 → 写代码 / 开会 / 测试
- 学习 → 学数学 / 学英语 / 看书

## API 接口

| 接口 | 说明 |
|-----|------|
| `GET /api/statistics/by-level` | 按层级获取统计 |
| `GET /api/statistics/by-category` | 获取子分类统计 |
| `GET /api/categories` | 获取分类树 |

## 技术栈

- **后端**: Flask + SQLAlchemy
- **前端**: Tailwind CSS + ECharts
- **LLM**: OpenAI / DeepSeek API
