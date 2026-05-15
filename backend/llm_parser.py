import json
import re

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL


_SYSTEM_PROMPT = """你是一个把自然语言映射规则解析为 JSON 配置的工具。只输出一个 JSON 对象，不要输出任何解释、不要用 Markdown 代码块包裹。

JSON 配置结构：
{
  "key_mapping": { "user_col": "用户表主键列引用", "sys_col": "系统表主键列名" },
  "filters": [
    { "column": "用户表列引用", "operator": "equals|contains|not_equals", "value": "字符串" }
  ],
  "mappings": [
    { "type": "copy", "source_column": "用户表列引用", "target_column": "系统表列名" },
    {
      "type": "conditional",
      "source_column": "用户表列引用",
      "conditions": [
        {
          "operator": "equals|contains|not_equals|in",
          "value": "字符串 或 字符串数组(operator=in 时)",
          "target_column": "系统表列名",
          "target_value": "命中时写入的固定值"
        }
      ],
      "default": { "target_column": "系统表列名", "target_value": "兜底值" }
    },
    {
      "type": "compute",
      "function": "max_date|min_date|max_num|min_num|concat",
      "source_columns": ["用户表列引用1", "用户表列引用2"],
      "target_column": "系统表列名"
    }
  ]
}

【表头说明】
两张表都是双层表头。系统表第 1 行是属性名或活动名（活动名横向合并多列），第 2 行是子列名；用户表同样规则，但第 1 行可能整行为空。

【列引用规则】
- 系统表列：用扁平名。属性列直接写名字（如 "EMP_ID"）；活动子列写 "活动名.子列名"（如 "活动A.计划开始时间"）。必须从给定的「系统表字段列表」中精确匹配。
- 用户表列（source/key）：支持两种写法，二选一：
  (a) 扁平字段名（如 "工号" 或 "活动A.计划开始时间"），从给定的「用户表字段列表」中精确匹配；
  (b) Excel 列字母 + "列" 后缀（如 "P列"、"AH列"、"CA列"），从给定的「用户表列字母对照」中精确匹配。
- 用户原文里出现的 "[X列]" 写法，X 看起来像 1~3 个字母时（A-Z, AH, CA, EG 等）是 Excel 列字母引用，否则是字段名引用。

【其它规则】
1. 主键声明只允许一条；多条筛选条件之间是 AND 关系。
2. 「如果 A 等于 X 或 Y → ...」这类规则使用 conditional + operator=in。
3. 「否则 → ...」使用 default 字段。
4. 「较晚的日期/较早的日期」对应 max_date / min_date；「最大数/最小数」对应 max_num / min_num。
5. filters 没有时输出空数组 []，mappings 没有时输出空数组 []。
6. 如果用户规则里的列引用在两个对照表中都找不到，仍按用户原文输出该字段的字符串值；后端会再做一次解析，如仍解析不出会在执行日志里以 warning 的形式给出。
"""


def _extract_json(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def _format_letter_map(letter_map: dict[str, str]) -> str:
    if not letter_map:
        return "(空)"
    items = sorted(letter_map.items(), key=lambda kv: (len(kv[0]), kv[0]))
    return ", ".join(f"{letter}列={name}" for letter, name in items)


def parse_rules(
    user_headers: list[str],
    sys_headers: list[str],
    user_letter_map: dict[str, str],
    rules_text: str,
) -> dict:
    user_msg = (
        f"用户表字段列表（扁平后）：\n{json.dumps(user_headers, ensure_ascii=False)}\n\n"
        f"用户表列字母对照（Excel 列字母 → 字段名）：\n{_format_letter_map(user_letter_map)}\n\n"
        f"系统表字段列表（扁平后）：\n{json.dumps(sys_headers, ensure_ascii=False)}\n\n"
        f"用户规则：\n{rules_text}\n\n"
        "请严格按 schema 输出 JSON 配置。"
    )

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        temperature=0,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    raw = "".join(text_parts).strip()
    if not raw:
        raise ValueError("LLM 返回为空")

    payload = _extract_json(raw)
    try:
        config = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 输出不是合法 JSON: {e.msg}; 原始输出: {raw[:500]}") from e

    if not isinstance(config, dict):
        raise ValueError("LLM 输出的 JSON 顶层不是对象")

    config.setdefault("filters", [])
    config.setdefault("mappings", [])
    return config
