import React from "react";

export default function SheetSelector({ label, sheets, value, onChange, disabled }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || sheets.length === 0}
        className="w-full px-3 py-2 text-sm border border-slate-300 rounded bg-white disabled:bg-slate-100 disabled:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
      >
        <option value="">{sheets.length === 0 ? "请先上传文件" : "请选择 Sheet"}</option>
        {sheets.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
    </div>
  );
}
