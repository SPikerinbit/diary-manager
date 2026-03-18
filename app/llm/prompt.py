# llm/prompt.py
# 大模型提示词模板


TIME_EXTRACTION_PROMPT = """你是一个时间数据分析助手。你的任务是从日记内容中提取时间块信息。

## 输出格式
请严格按照以下JSON格式输出，不要添加任何解释：

{
  "time_blocks": [
    {
      "date": "2026-03-18",
      "activity": "学数学",
      "duration_minutes": 120,
      "category_path": ["学习", "学数学"],
      "notes": "做了高等数学练习题"
    }
  ]
}

## 提取规则
1. date: 日期，格式 YYYY-MM-DD
2. activity: 活动名称（简洁）
3. duration_minutes: 时长，必须转换为分钟数
4. category_path: 分类路径，数组形式，如 ["学习", "学数学", "高等数学"]
   - 第一层: 学习/睡觉/玩耍/吃饭/工作（从配置的大类选择）
   - 如果日记中没有明确分类，尽量归入最合适的现有分类
5. notes: 可选的备注说明

## 重要约束
- 只输出JSON，不要有其他文字
- 如果无法确定日期或时长，设置该字段为null
- duration_minutes 必须是整数
- 从文本中推断时间（如"学了2小时" = 120分钟，"看了半小时" = 30分钟）
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
