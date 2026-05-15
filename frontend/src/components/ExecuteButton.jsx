import React from "react";

export default function ExecuteButton({ onClick, disabled, executing }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="w-full px-4 py-2.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed rounded transition flex items-center justify-center gap-2"
    >
      {executing && (
        <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
      )}
      {executing ? "正在解析并执行…" : "解析并执行"}
    </button>
  );
}
