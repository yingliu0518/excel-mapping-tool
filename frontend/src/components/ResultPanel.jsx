import React, { useState } from "react";

function StatBlock({ label, value, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-50 text-slate-700",
    green: "bg-green-50 text-green-700",
    amber: "bg-amber-50 text-amber-700",
  };
  return (
    <div className={`flex-1 px-4 py-3 rounded ${tones[tone]}`}>
      <div className="text-xs">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
    </div>
  );
}

export default function ResultPanel({ result }) {
  const [tab, setTab] = useState("log");
  const { downloadUrl, log } = result;

  return (
    <div className="border border-slate-200 bg-white rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
        <div className="flex gap-1">
          <button
            onClick={() => setTab("log")}
            className={`px-3 py-1.5 text-sm rounded ${
              tab === "log" ? "bg-white border border-slate-300 text-slate-900" : "text-slate-500"
            }`}
          >
            执行日志
          </button>
          <button
            onClick={() => setTab("config")}
            className={`px-3 py-1.5 text-sm rounded ${
              tab === "config" ? "bg-white border border-slate-300 text-slate-900" : "text-slate-500"
            }`}
          >
            结构化配置
          </button>
        </div>
        <a
          href={downloadUrl}
          download="系统表_已填充.xlsx"
          className="px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 text-white rounded"
        >
          下载结果文件
        </a>
      </div>

      <div className="p-4">
        {tab === "log" && (
          <div className="space-y-4">
            <div className="flex gap-3">
              <StatBlock label="筛选行数" value={log?.filtered_count ?? 0} />
              <StatBlock label="更新行数" value={log?.updated_count ?? 0} tone="green" />
              <StatBlock label="跳过行数" value={log?.skipped_count ?? 0} tone="amber" />
            </div>

            {log?.skipped_keys?.length > 0 && (
              <div>
                <div className="text-sm font-medium text-slate-700 mb-1">
                  跳过的主键值（系统表中未找到匹配行）
                </div>
                <div className="max-h-40 overflow-auto p-2 bg-slate-50 border border-slate-200 rounded text-xs font-mono">
                  {log.skipped_keys.map((k, i) => (
                    <div key={i}>{k || "(空)"}</div>
                  ))}
                </div>
              </div>
            )}

            {log?.warnings?.length > 0 && (
              <div>
                <div className="text-sm font-medium text-amber-700 mb-1">警告</div>
                <ul className="list-disc list-inside text-sm text-amber-700 space-y-0.5">
                  {log.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {log?.filtered_count === 0 && (
              <div className="text-sm text-slate-500">筛选结果为 0 行，未更新任何数据。</div>
            )}
          </div>
        )}

        {tab === "config" && (
          <pre className="text-xs leading-5 p-3 bg-slate-50 border border-slate-200 rounded overflow-auto max-h-96">
            {JSON.stringify(log?.config ?? {}, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
