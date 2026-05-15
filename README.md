# Excel 字段映射填充工具

需求与技术方案见 [`Excel字段映射填充工具_技术方案.md`](./Excel字段映射填充工具_技术方案.md)。

## 目录结构

```
backend/    FastAPI + openpyxl + Anthropic SDK
frontend/   React + Vite + Tailwind CSS
```

## 启动

### 1. 配置 API Key

编辑 `backend/config.py`，把 `ANTHROPIC_API_KEY` 替换成自己的 key。

### 2. 启动后端

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

启动后访问 http://localhost:8000/docs 可以看到 FastAPI Swagger UI。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173 使用工具。Vite dev server 已配置 `/api` proxy 到 8000 端口。

## 表格格式约定

工具假设两张表都是**双层表头**：

- 系统表
  - 第 1 行：属性名（与第 2 行垂直合并）或 活动名（横向合并若干列）
  - 第 2 行：活动下的子列名
  - 第 3 行：计数行（无业务意义，自动跳过）
  - 第 4 行起：数据
- 用户表
  - 第 1 行：可能为空，或为横向合并的活动名
  - 第 2 行：具体列名 / 子列名
  - 第 3 行起：数据

表头会自动扁平化为：
- 纯属性 → `属性名`（如 `EMP_ID`）
- 活动子列 → `活动名.子列名`（如 `活动A.计划开始时间`）

## 规则中的列引用

- 系统表：用扁平后的列名，如 `系统表[EMP_ID]`、`系统表[活动A.计划开始时间]`
- 用户表：两种写法都可以
  - 字段名：`[工号]`、`[活动A.计划开始时间]`
  - Excel 列字母 + "列" 后缀：`[P列]`、`[AH列]`、`[CA列]`

## 使用流程

1. 上传用户表（.xlsx）和系统表（.xlsx）
2. 两侧 Sheet 列表自动加载，分别选择要处理的 Sheet
3. 在文本框输入自然语言映射规则（参考占位提示中的示例）
4. 点击「解析并执行」
5. 在结果面板下载填充完成的 .xlsx，或在两个 Tab 查看执行日志和 LLM 解析出的 JSON 配置
