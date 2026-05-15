# Excel 字段映射填充工具 · 需求与技术方案

---

## 一、背景与目标

### 1.1 背景

业务团队日常维护一张**用户表**（Excel），需要定期将其中的数据同步填入**系统表**（从系统导出的 Excel 模板）。系统表字段繁多、结构复杂，手动填写效率极低且容易出错。

### 1.2 目标

构建一个工具，让用户只需：
1. 上传用户表和系统表
2. 用自然语言描述转换规则
3. 点击执行，自动得到填充完成的系统表

### 1.3 核心约束

- 用户表和系统表的格式**每次可能不同**，工具不能写死字段名
- 转换规则由用户在运行时输入，不是预设的
- 采用**前后端分离架构**：前端负责界面交互，后端（Python）负责 Excel 处理与转换执行，LLM 解析规则时调用 Anthropic API

---

## 二、功能需求

### 2.1 用户操作流程

```
第一步：上传文件
  用户在页面上传用户表（.xlsx）和系统表（.xlsx）

第二步：选择 Sheet
  工具自动读取两个文件各自的 Sheet 页列表
  用户分别选择要处理的 Sheet 页

第三步：输入转换规则
  用户用自然语言输入规则（见 2.2 节）

第四步：执行
  点击"解析并执行"按钮
  后端调用 LLM 解析规则 → 生成结构化配置 → 执行转换 → 返回结果文件

第五步：获取结果
  页面提供下载按钮，下载填充完成的系统表（.xlsx）
  页面展示执行日志（处理行数、跳过行数、错误信息）
```

### 2.2 转换规则语法

用户用自然语言输入规则，工具通过 LLM 解析。规则由以下几类语句组成：

#### ① 主键声明（必填，且只能有一条）

声明用户表和系统表之间用哪列进行行匹配。工具根据主键在系统表中找到对应行，再执行赋值。

```
主键：用户表[列名A] 对应 系统表[列名B]
```

#### ② 筛选条件（可选，可多条）

从用户表中筛选出需要处理的行。多条筛选条件之间为 **AND** 关系，所有条件均满足才处理该行。

支持三种运算符：

| 运算符 | 含义 | 示例 |
|--------|------|------|
| 等于 | 列的值完全等于指定值 | `筛选：[P列] 等于 正式` |
| 包含 | 列的值包含指定字符串 | `筛选：[F列] 包含 项目` |
| 不等于 | 列的值不等于指定值 | `筛选：[状态列] 不等于 离职` |

#### ③ 赋值操作（可多条，不限数量）

支持三种赋值类型：

**类型一：直接复制**

将用户表某列的值原样写入系统表某列。

```
复制 [用户表列名] → 系统表[系统表列名]
```

**类型二：条件赋值**

根据用户表某列的值，决定向系统表写入什么固定值。支持：
- 多个值命中同一结果（OR 逻辑，用"或"连接）
- 兜底默认值（用"否则"表示，当所有条件都不满足时执行）

```
如果 [列名] 等于 值A 或 值B → 系统表[列名] = 结果1
否则 → 系统表[列名] = 结果2
```

**类型三：跨列计算**

对用户表的多列数据进行计算，将结果写入系统表。

```
取 [列名A] 与 [列名B] 中较晚的日期 → 系统表[列名]
取 [列名A] 与 [列名B] 中较早的日期 → 系统表[列名]
```

### 2.3 已知业务规则示例

以下为当前实际业务场景中的规则，工具必须能正确处理：

```
主键：用户表[工号列] 对应 系统表[EMP_ID]

筛选：[P列] 等于 XX
筛选：[F列] 包含 XX

如果 [AH列] 等于 已交付 或 默认完工 → 系统表[完工场景字段] = 场景1
否则 → 系统表[完工场景字段] = 场景2

复制 [CA列] → 系统表[XX字段]

取 [EG列] 与 [EV列] 中较晚的日期 → 系统表[XX字段]
```

### 2.4 执行结果要求

- 输出文件为 .xlsx，保留系统表原有的表头结构，仅更新匹配到的行和字段
- 未在用户表中找到主键匹配的系统表行，保持原值不变
- 页面展示执行日志，包含：筛选行数、成功更新行数、跳过行数及原因

---

## 三、技术方案

### 3.1 整体架构

采用前后端分离架构，**LLM 只负责解析规则，不参与数据执行**：

```
浏览器（前端）
┌─────────────────────────────────┐
│  上传文件 / 选 Sheet / 输入规则  │
│  展示日志 / 下载结果文件         │
└────────────┬────────────────────┘
             │ HTTP 请求
             ▼
后端服务（Python）
┌─────────────────────────────────┐
│                                 │
│  接收文件 + 规则文本             │
│          │                      │
│          ▼                      │
│   调用 Anthropic API            │
│   LLM 解析规则 → JSON 配置      │
│          │                      │
│          ▼                      │
│   execute_mapping()             │
│   确定性转换函数（openpyxl）     │
│          │                      │
│          ▼                      │
│   返回填充完成的 .xlsx           │
└─────────────────────────────────┘
```

**为什么这样设计：**
- LLM 输出不稳定，不能让 LLM 直接操作数据，只用它做语义解析
- 转换函数接收结构化 JSON 入参，行为完全确定，结果可复现、可调试
- 后端用 Python 处理 Excel，openpyxl 对复杂格式、大数据量的支持优于浏览器端方案
- 出现问题时可直接查看 LLM 输出的 JSON，快速定位是规则解析问题还是执行问题

### 3.2 技术选型

| 模块 | 技术 | 说明 |
|------|------|------|
| 前端界面 | React | 文件上传、Sheet 选择、规则输入、日志展示、结果下载 |
| 后端服务 | Python / FastAPI | 接收请求、调用 LLM、执行转换、返回文件 |
| Excel 读写 | openpyxl | 读取 .xlsx、按主键更新行、保留原有格式输出 |
| LLM 解析 | Anthropic API（claude-sonnet） | 自然语言规则 → JSON 配置，每次执行只调用一次 |
| 转换执行 | Python 纯函数 | 无外部依赖，逻辑确定，易于单元测试 |

### 3.3 接口设计

#### 接口一：获取 Sheet 列表

上传文件后，前端调用此接口获取各文件的 Sheet 页名称，填充下拉选择器。

```
POST /api/sheets
Content-Type: multipart/form-data

参数：
  user_file: 用户表文件（.xlsx）
  sys_file:  系统表文件（.xlsx）

返回：
{
  "user_sheets": ["Sheet1", "Sheet2", ...],
  "sys_sheets":  ["Sheet1", "Sheet2", ...]
}
```

#### 接口二：执行转换

```
POST /api/execute
Content-Type: multipart/form-data

参数：
  user_file:       用户表文件（.xlsx）
  sys_file:        系统表文件（.xlsx）
  user_sheet:      用户表所选 Sheet 名称
  sys_sheet:       系统表所选 Sheet 名称
  rules:           用户输入的自然语言规则（字符串）

返回（成功）：
  Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  Content-Disposition: attachment; filename="系统表_已填充.xlsx"
  Body: 填充完成的 .xlsx 文件二进制内容

  Header 附加：
  X-Execute-Log: {"filtered_count": 100, "updated_count": 85, "skipped_count": 15,
                  "skipped_keys": ["K001", "K002"], "config": {...}}

返回（失败）：
  HTTP 400 / 500
  { "error": "错误描述" }
```

### 3.4 LLM 解析层

#### 调用时机

在 `/api/execute` 接口内，读取两张表的表头后，立即调用 LLM 解析规则。LLM 每次请求只调用一次。

#### 传给 LLM 的内容

- 用户表的字段列表（从所选 Sheet 第一行表头读取）
- 系统表的字段列表（从所选 Sheet 第一行表头读取）
- 用户输入的自然语言规则文本

#### Prompt 设计要求

- System prompt 中给出完整的 JSON Schema 定义，要求 LLM **只输出 JSON**，不输出任何解释文字
- 字段名必须从给定字段列表中**精确匹配**，不能凭空生成
- 规则中提到的字段名若无法在字段列表中找到，对应字段标记为 `null`
- 后端收到响应后做 JSON 合法性校验，不合法则返回 400 错误

#### LLM 输出的 JSON 结构示例

```json
{
  "key_mapping": {
    "user_col": "工号列",
    "sys_col": "EMP_ID"
  },
  "filters": [
    { "column": "P列", "operator": "equals", "value": "XX" },
    { "column": "F列", "operator": "contains", "value": "XX" }
  ],
  "mappings": [
    {
      "type": "conditional",
      "source_column": "AH列",
      "conditions": [
        {
          "operator": "in",
          "value": ["已交付", "默认完工"],
          "target_column": "完工场景字段",
          "target_value": "场景1"
        }
      ],
      "default": {
        "target_column": "完工场景字段",
        "target_value": "场景2"
      }
    },
    {
      "type": "copy",
      "source_column": "CA列",
      "target_column": "XX字段"
    },
    {
      "type": "compute",
      "function": "max_date",
      "source_columns": ["EG列", "EV列"],
      "target_column": "XX字段"
    }
  ]
}
```

### 3.5 JSON Schema 完整定义

```
Config
├── key_mapping（必填）
│   ├── user_col: str               # 用户表主键列名
│   └── sys_col: str                # 系统表主键列名
│
├── filters: List（可选，空列表表示不筛选）
│   └── 每一项：
│       ├── column: str             # 筛选列名
│       ├── operator: enum          # equals | contains | not_equals
│       └── value: str              # 筛选值
│       多条 filter 之间为 AND 关系
│
└── mappings: List（可多条，不限数量）
    │
    ├── type = "copy"               直接复制
    │   ├── source_column: str      # 用户表来源列
    │   └── target_column: str      # 系统表目标列
    │
    ├── type = "conditional"        条件赋值
    │   ├── source_column: str      # 判断依据列（用户表）
    │   ├── conditions: List
    │   │   ├── operator: enum      # equals | contains | not_equals | in
    │   │   ├── value: str          # 单值判断（equals / contains / not_equals）
    │   │         或 List[str]      # 多值判断（in，命中其中任一即为 true）
    │   │   ├── target_column: str  # 系统表目标列
    │   │   └── target_value: str   # 命中时写入的固定值
    │   └── default（可选）         # 所有 conditions 均未命中时的兜底
    │       ├── target_column: str
    │       └── target_value: str
    │
    └── type = "compute"            跨列计算
        ├── function: enum          # 见下方计算函数表
        ├── source_columns: List[str]  # 参与计算的用户表列名列表
        └── target_column: str      # 系统表目标列
```

**计算函数表**

| function 值 | 行为 |
|-------------|------|
| `max_date` | 取 source_columns 各列的日期值，返回最晚的一个 |
| `min_date` | 取 source_columns 各列的日期值，返回最早的一个 |
| `max_num` | 取 source_columns 各列的数值，返回最大值 |
| `min_num` | 取 source_columns 各列的数值，返回最小值 |
| `concat` | 将 source_columns 各列的值拼接为字符串 |

### 3.6 转换函数层（Python）

函数签名：

```python
def execute_mapping(config: dict, user_df: pd.DataFrame, sys_wb: openpyxl.Workbook, sys_sheet: str) -> openpyxl.Workbook:
```

参数说明：
- `config`：LLM 解析出的结构化 JSON 配置
- `user_df`：用 pandas 读取的用户表 DataFrame
- `sys_wb`：用 openpyxl 读取的系统表 Workbook（保留原始格式）
- `sys_sheet`：系统表所选 Sheet 名称

返回：更新后的系统表 Workbook，直接写出为 .xlsx 返回给前端。

> 用户表用 pandas 读取便于筛选和行遍历；系统表用 openpyxl 读取，目的是**保留原有单元格格式**（字体、颜色、边框等），只更新值，不破坏样式。

#### 执行逻辑伪代码

**Step 1：筛选用户表数据**

```python
filtered_df = user_df.copy()
for f in config["filters"]:
    col, op, val = f["column"], f["operator"], f["value"]
    col_data = filtered_df[col].astype(str)
    if op == "equals":
        filtered_df = filtered_df[col_data == val]
    elif op == "contains":
        filtered_df = filtered_df[col_data.str.contains(val, na=False)]
    elif op == "not_equals":
        filtered_df = filtered_df[col_data != val]
```

**Step 2：建系统表主键索引**

```python
ws = sys_wb[sys_sheet]
headers = [cell.value for cell in ws[1]]          # 第一行为表头
sys_key_col = config["key_mapping"]["sys_col"]
sys_key_idx = headers.index(sys_key_col)          # 主键列在表头中的位置

# 行号从 2 开始（第 1 行是表头）
sys_index = {}
for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
    key_val = str(row[sys_key_idx].value or "")
    if key_val:
        sys_index[key_val] = row_num
```

**Step 3：逐行映射**

```python
updated_count = 0
skipped_keys = []
user_key_col = config["key_mapping"]["user_col"]

for _, user_row in filtered_df.iterrows():
    key_val = str(user_row[user_key_col])
    row_num = sys_index.get(key_val)
    if row_num is None:
        skipped_keys.append(key_val)
        continue

    for mapping in config["mappings"]:

        if mapping["type"] == "copy":
            value = user_row[mapping["source_column"]]
            col_idx = headers.index(mapping["target_column"])
            ws.cell(row=row_num, column=col_idx + 1).value = value

        elif mapping["type"] == "conditional":
            src_val = str(user_row[mapping["source_column"]])
            matched = False
            for condition in mapping["conditions"]:
                hit = False
                if condition["operator"] == "equals":
                    hit = src_val == condition["value"]
                elif condition["operator"] == "contains":
                    hit = condition["value"] in src_val
                elif condition["operator"] == "not_equals":
                    hit = src_val != condition["value"]
                elif condition["operator"] == "in":
                    hit = src_val in condition["value"]
                if hit:
                    col_idx = headers.index(condition["target_column"])
                    ws.cell(row=row_num, column=col_idx + 1).value = condition["target_value"]
                    matched = True
                    break
            if not matched and "default" in mapping:
                col_idx = headers.index(mapping["default"]["target_column"])
                ws.cell(row=row_num, column=col_idx + 1).value = mapping["default"]["target_value"]

        elif mapping["type"] == "compute":
            result = compute_functions[mapping["function"]](user_row, mapping["source_columns"])
            col_idx = headers.index(mapping["target_column"])
            ws.cell(row=row_num, column=col_idx + 1).value = result

    updated_count += 1

return sys_wb, updated_count, skipped_keys
```

**Step 4：计算函数实现**

```python
from datetime import datetime

def parse_date(val):
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except Exception:
        return None

compute_functions = {
    "max_date": lambda row, cols: max(
        (d for c in cols if (d := parse_date(row[c])) is not None), default=""
    ),
    "min_date": lambda row, cols: min(
        (d for c in cols if (d := parse_date(row[c])) is not None), default=""
    ),
    "max_num": lambda row, cols: max(
        (n for c in cols if (n := pd.to_numeric(row[c], errors="coerce")) and not pd.isna(n)), default=""
    ),
    "min_num": lambda row, cols: min(
        (n for c in cols if (n := pd.to_numeric(row[c], errors="coerce")) and not pd.isna(n)), default=""
    ),
    "concat": lambda row, cols: "".join(str(row[c]) for c in cols),
}
```

---

## 四、异常处理要求

| 异常场景 | 处理方式 |
|----------|----------|
| LLM 返回非合法 JSON | 后端捕获解析异常，返回 HTTP 400，前端展示错误信息，不输出文件 |
| LLM 解析出的字段名在表头中不存在 | 执行时 `headers.index()` 抛出 ValueError，跳过该 mapping，日志中警告 |
| 用户未填写主键声明 | LLM 解析后 `key_mapping` 为 null，后端执行前校验，返回 400 提示用户补充 |
| 主键列在系统表中找不到匹配行 | 跳过该行，`skipped_keys` 记录主键值，不影响其他行处理 |
| 筛选后用户表数据为空 | 正常返回，日志提示"筛选结果为 0 行，未更新任何数据" |
| conditional 无条件命中且无 default | 该字段保留系统表原值，不做任何修改 |
| compute 列值无法解析为有效日期/数值 | 过滤无效值后计算剩余列；若全部无效则写入空字符串，日志警告 |
| 上传文件非 .xlsx 格式 | 后端校验文件扩展名和 MIME 类型，不符合则返回 400 |

---

## 五、界面交互要求

- 文件上传后自动调用 `/api/sheets` 获取 Sheet 列表并填充下拉框
- 文件上传区域显示已上传文件名，支持重新上传覆盖
- 规则输入框提供 placeholder 示例引导用户填写
- 点击"解析并执行"后按钮置灰，展示加载状态，防止重复提交
- 执行完成后展示日志面板，包含两个 Tab：
  - **执行日志**：筛选行数、更新行数、跳过行数及跳过的主键值列表
  - **结构化配置**：展示 LLM 解析出的 JSON，供用户核查规则是否被正确理解
- 执行成功后提供下载按钮，文件名为 `系统表_已填充.xlsx`
