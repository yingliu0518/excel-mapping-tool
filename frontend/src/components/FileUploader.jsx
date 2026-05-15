import React, { useRef } from "react";

export default function FileUploader({ label, file, onChange }) {
  const inputRef = useRef(null);

  const handleClick = () => inputRef.current?.click();
  const handleChange = (e) => {
    const f = e.target.files?.[0];
    if (f) onChange(f);
    e.target.value = "";
  };

  return (
    <div className="border border-dashed border-slate-300 bg-white rounded-lg p-4 hover:border-slate-400 transition">
      <div className="text-sm font-medium text-slate-700 mb-2">{label}</div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleClick}
          className="px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-300"
        >
          选择文件
        </button>
        <span className="text-sm text-slate-500 truncate">
          {file ? file.name : "未选择 .xlsx 文件"}
        </span>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={handleChange}
        />
      </div>
    </div>
  );
}
