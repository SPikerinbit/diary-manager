# llm/prompt.py
# 大模型提示词模板


TIME_POINT_EXTRACTION_PROMPT = """你是一个时间数据分析助手。你的任务是从日记中提取完整的时间点序列。

## 日记日期
{date}

## 输出格式
请严格按照以下JSON格式输出，不要添加任何解释：

{{
  "time_points": [
    {{"time": "07:00", "event": "起床"}},
    {{"time": "22:00", "event": "睡觉"}}
  ]
}}

## 提取规则
1. time: 时间点，格式为 HH:MM（24小时制）
2. event: 事件描述

## 严格规则
- 必须输出完整的时间序列，从起床到睡觉
- 时间点之间不能有任何空隙
- 所有时间点加起来必须等于24小时

## 事件类型
- 起床、睡觉
- 整理仪容仪表、吃早餐、吃午饭、吃晚饭
- 通勤、工作、学习
- 玩耍

## 只输出JSON
"""


EVENT_DETAIL_PROMPT = """你是一个时间分析助手。根据以下日记内容和时间点序列，用简洁常见的词组描述每个事件在做什么。

## 日记内容
{diary_content}

## 时间点序列
{time_points}

## 输出格式
请严格按照以下JSON格式输出：

{{
  "details": [
    {{"event": "起床", "detail": "具体做什么"}},
    {{"event": "工作", "detail": "具体做什么"}},
    ...
  ]
}}

## 规则
- detail使用简洁常见的词组，如：醒脑、穿衣、早餐、通勤、开会、写代码、学习数学、英语、午餐、休息、锻炼、游戏、追剧、晚餐、洗澡等
- 如果日记没提到具体内容，根据事件类型给一个合理的常见词组
- 不要照搬日记原文，要用常见的词组
- 只输出JSON
"""


CATEGORY_CLASSIFY_PROMPT = """你是一个分类助手。请为以下事件列表确定分类路径。

## 已有分类体系
{categories}

## 输入格式
{{
  "events": [
    {{"event": "起床", "duration": 10}},
    {{"event": "吃早餐", "duration": 30}},
    {{"event": "通勤", "duration": 60}},
    {{"event": "工作", "duration": 480}},
    {{"event": "吃午饭", "duration": 60}},
    ...
  ]
}}

## 输出格式
请严格按照以下JSON格式输出：

{{
  "classified": [
    {{"event": "起床", "duration": 10, "category_path": ["睡觉", "起床"]}},
    {{"event": "吃早餐", "duration": 30, "category_path": ["吃饭", "早餐"]}},
    {{"event": "通勤", "duration": 60, "category_path": ["通勤"]}},
    {{"event": "工作", "duration": 480, "category_path": ["工作", "日常工作"]}},
    ...
  ]
}}

## 分类规则
- 工作相关 → ["工作", "具体工作内容"]
- 学习相关 → ["学习", "具体学习内容"]
- 睡觉/休息 → ["睡觉"]
- 玩耍/娱乐 → ["玩耍", "具体娱乐内容"]
- 吃饭 → ["吃饭", "早餐/午餐/晚餐/夜宵"]
- 通勤 → ["通勤"]
- 发呆/放空 → ["睡觉", "休息"]

## 重要规则
- 必须为每个event分配一个category_path
- category_path必须以根分类开头
- 只输出JSON，不要有其他文字
"""


REFINE_PROMPT = """你是一个时间数据分析助手。请根据以下活动信息，进一步细化具体的子分类。

## 父分类
{parent_category}

请严格按照以下JSON格式输出：

{{
  "time_blocks": [
    {{
      "activity": "具体的活动名称",
      "category_path": ["父分类", "子分类"]
    }}
  ]
}}

## 细化规则
- 根据activity的具体内容，给出更准确的分类
- 如果已有子分类合适，直接使用
- category_path必须以父分类开头
- 只输出JSON
"""


WEEKLY_SUMMARY_PROMPT = """你是一个数据分析助手。请根据以下一周的时间记录生成简洁的总结。

## 输入数据
{data}

## 输出格式
请严格按照以下JSON格式输出：

{
  "summary": {
    "total_hours": 总小时数,
    "top_categories": [
      {"name": "分类名", "hours": 小时数, "percentage": 百分比}
    ],
    "insights": ["洞察1", "洞察2"],
    "recommendations": ["建议1", "建议2"]
  }
}

## 注意事项
- 只输出JSON
- percentage为百分比，如25.5表示25.5%
- insights和recommendations各提供2-3条
"""


REFINE_PROMPT = """你是一个时间数据分析助手。请根据以下活动信息，进一步细化具体的子分类。

## 父分类
{parent_category}

请严格按照以下JSON格式输出：

{{
  "time_blocks": [
    {{
      "activity": "具体的活动名称",
      "category_path": ["父分类", "子分类"]
    }}
  ]
}}

## 细化规则
- 根据activity的具体内容，给出更准确的分类
- 如果已有子分类合适，直接使用
- 如果需要创建新子分类，请创建
- 例如：
  - 父分类=学习，activity=听课 -> category_path: ["学习", "听课"]
  - 父分类=工作，activity=写文档 -> category_path: ["工作", "写文档"]
  - 父分类=玩耍，activity=打游戏 -> category_path: ["玩耍", "打游戏"]

## 重要约束
- 只输出JSON
- category_path必须以父分类开头
"""


WEEKLY_SUMMARY_PROMPT = """你是一个数据分析助手。请根据以下一周的时间记录生成简洁的总结。

## 输入数据
{data}

## 输出格式
请严格按照以下JSON格式输出：

{
  "summary": {
    "total_hours": 总小时数,
    "top_categories": [
      {"name": "分类名", "hours": 小时数, "percentage": 百分比}
    ],
    "insights": ["洞察1", "洞察2"],
    "recommendations": ["建议1", "建议2"]
  }
}

## 注意事项
- 只输出JSON
- percentage为百分比，如25.5表示25.5%
- insights和recommendations各提供2-3条
"""


REFINE_PROMPT = """你是一个时间数据分析助手。请根据以下活动信息，进一步细化具体的子分类。

## 父分类
{parent_category}

请严格按照以下JSON格式输出：

{{
  "time_blocks": [
    {{
      "activity": "具体的活动名称",
      "category_path": ["父分类", "子分类"]
    }}
  ]
}}

## 细化规则
- 根据activity的具体内容，给出更准确的分类
- 如果已有子分类合适，直接使用
- 如果需要创建新子分类，请创建
- 例如：
  - 父分类=学习，activity=听课 -> category_path: ["学习", "听课"]
  - 父分类=工作，activity=写文档 -> category_path: ["工作", "写文档"]
  - 父分类=玩耍，activity=打游戏 -> category_path: ["玩耍", "打游戏"]

## 重要约束
- 只输出JSON
- category_path必须以父分类开头
"""


WEEKLY_SUMMARY_PROMPT = """你是一个数据分析助手。请根据以下一周的时间记录生成简洁的总结。

## 输入数据
{data}

## 输出格式
请严格按照以下JSON格式输出：

{
  "summary": {
    "total_hours": 总小时数,
    "top_categories": [
      {"name": "分类名", "hours": 小时数, "percentage": 百分比}
    ],
    "insights": ["洞察1", "洞察2"],
    "recommendations": ["建议1", "建议2"]
  }
}

## 注意事项
- 只输出JSON
- percentage为百分比，如25.5表示25.5%
- insights和recommendations各提供2-3条
"""
