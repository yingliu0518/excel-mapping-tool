import json
import re

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL


_SYSTEM_PROMPT = """你是一个把自然语言映射规则解析为 JSON 配置的工具。只能输出一个 JSON 对象，不要输出任何解释、不要用 Markdown 代码块包裹。

JSON 配置结构：

{
  "key_mapping": { "user_col": "用户表主键列名", "sys_col": "系统表主键列名" },
  "filters": [
    { "column": "用户表列名", "operator": "equals|contains|not_equals", "value": "字符串" }
  ],
  "mappings": [
    { "type": "copy", "source_column": "用户表列名", "target_column": "系统表列名" },
    {
      "type": "conditional",
      "source_column": "用户表列名",
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
      "source_columns": ["用户表列名1", "用户表列名2"],
      "target_column": "系统表列名"
    }
  ]
}

规则：
1. 字段名必须从给定的「用户表字段列表」「系统表字段列表」中精确匹配，不能凭空生成。
2. 如果用户规则里提到的列名在对应字段列表中找不到，把该字段值设为 null（不要省略字段）。
3. 主键声明只允许一条；多条筛选条件之间是 AND 关系。
4. 「如果 A 等于 X 或 Y → ...」这类规则使用 conditional + operator=in。
5. 「否则 → ...」使用 default 字段。
6. 「较晚的日期/较早的日期」对应 max_date / min_date；「最大数/最小数」对应 max_num / min_num。
7. filters 没有时输出空数组 [], mappings 没有时输出空数组 []。
"""


def _extract_json(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def parse_rules(user_headers: list[str], sys_headers: list[str], rules_text: str) -> dict:
    user_msg = (
        f"用户表字段列表：{json.dumps(user_headers, ensure_ascii=False)}\n"
        f"系统表字段列表：{json.dumps(sys_headers, ensure_ascii=False)}\n\n"
        f"用户规则：\n{rules_text}\n\n"
        "请输出 JSON 配置。"
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
