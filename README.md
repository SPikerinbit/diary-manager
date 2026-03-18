# 日记时间统计 Agent

一个自动化从日记文档中提取时间数据并生成统计可视化的工具。

## 功能特性

- 📄 支持 PDF、Markdown、Word 文档解析
- 🤖 大模型自动提取时间数据
- 🌳 动态分类树（从日记中自动发现新分类）
- 📊 Web界面可视化统计
- ⏰ 每周自动生成总结报告
- 🔄 自动处理文件（拖入即处理）

## 快速开始

### 1. 创建conda环境

```bash
# 使用environment.yml创建
conda env create -f environment.yml

# 或使用requirements.txt
conda create -n diary-time-tracker python=3.11
conda activate diary-time-tracker
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.yaml`，填入你的大模型API密钥：

```yaml
llm:
  api_key: "你的API密钥"  # 必填
  model: "gpt-4o-mini"    # 可选
```

### 3. 启动

```bash
python run.py
```

访问 http://localhost:5000

### 4. 使用

1. 将日记文档（PDF/MD/Word）拖入 `data/input/` 目录
2. Agent自动处理并提取时间数据
3. 打开Web界面查看统计

## 项目结构

```
diary-time-tracker/
├── config.yaml          # 配置文件
├── run.py               # 入口文件
├── app/
│   ├── models.py        # 数据库模型
│   ├── processor.py     # 核心处理逻辑
│   ├── watcher.py       # 文件监控
│   ├── parser/          # 文档解析
│   ├── llm/             # 大模型集成
│   ├── scheduler/       # 定时任务
│   └── routes/          # Web路由
├── templates/           # HTML模板
├── static/              # 静态资源
└── data/                # 数据目录
    ├── input/           # 待处理文件
    └── processed/      # 已处理文件
```

## 配置说明

| 配置项 | 说明 |
|--------|------|
| `llm.api_key` | 大模型API密钥 |
| `llm.model` | 使用的模型 |
| `app.port` | Web服务端口 |
| `scheduler.weekly_report_day` | 周报生成日 |

## 依赖环境

- Python 3.11+
- conda（推荐）或 pip
