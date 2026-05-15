import React from "react";

const PLACEHOLDER = `主键：用户表[工号列] 对应 系统表[EMP_ID]

筛选：[P列] 等于 正式
筛选：[F列] 包含 项目

如果 [AH列] 等于 已交付 或 默认完工 → 系统表[完工场景字段] = 场景1
否则 → 系统表[完工场景字段] = 场景2

复制 [CA列] → 系统表[XX字段]

取 [EG列] 与 [EV列] 中较晚的日期 → 系统表[XX字段]`;

export default function RuleEditor({ value, onChange }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        转换规则（自然语言）
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={PLACEHOLDER}
        rows={14}
        className="w-full px-3 py-2 text-sm border border-slate-300 rounded font-mono leading-6 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 resize-y"
      />
      <p className="text-xs text-slate-500 mt-1">
        必须包含一条「主键」声明；筛选 / 赋值规则可有多条。
      </p>
    </div>
  );
}
