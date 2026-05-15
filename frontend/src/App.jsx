import React, { useEffect, useState } from "react";
import FileUploader from "./components/FileUploader.jsx";
import SheetSelector from "./components/SheetSelector.jsx";
import RuleEditor from "./components/RuleEditor.jsx";
import ExecuteButton from "./components/ExecuteButton.jsx";
import ResultPanel from "./components/ResultPanel.jsx";
import { fetchSheets, executeMapping } from "./api.js";

export default function App() {
  const [userFile, setUserFile] = useState(null);
  const [sysFile, setSysFile] = useState(null);
  const [userSheets, setUserSheets] = useState([]);
  const [sysSheets, setSysSheets] = useState([]);
  const [userSheet, setUserSheet] = useState("");
  const [sysSheet, setSysSheet] = useState("");
  const [rules, setRules] = useState("");
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loadingSheets, setLoadingSheets] = useState(false);

  useEffect(() => {
    if (!userFile || !sysFile) return;
    let cancelled = false;
    setLoadingSheets(true);
    setError(null);
    fetchSheets(userFile, sysFile)
      .then(({ user_sheets, sys_sheets }) => {
        if (cancelled) return;
        setUserSheets(user_sheets);
        setSysSheets(sys_sheets);
        if (user_sheets.length === 1) setUserSheet(user_sheets[0]);
        if (sys_sheets.length === 1) setSysSheet(sys_sheets[0]);
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoadingSheets(false));
    return () => {
      cancelled = true;
    };
  }, [userFile, sysFile]);

  const onChangeUserFile = (f) => {
    setUserFile(f);
    setUserSheets([]);
    setUserSheet("");
    setResult(null);
  };
  const onChangeSysFile = (f) => {
    setSysFile(f);
    setSysSheets([]);
    setSysSheet("");
    setResult(null);
  };

  const canExecute =
    userFile && sysFile && userSheet && sysSheet && rules.trim() && !executing;

  const handleExecute = async () => {
    setExecuting(true);
    setError(null);
    setResult(null);
    try {
      const r = await executeMapping({
        userFile,
        sysFile,
        userSheet,
        sysSheet,
        rules,
      });
      setResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="min-h-full">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-4">
          <h1 className="text-lg font-semibold text-slate-900">
            Excel 字段映射填充工具
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            上传两张表 → 用自然语言描述映射规则 → 自动生成填充完成的系统表
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-700">第一步：上传文件</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FileUploader label="用户表" file={userFile} onChange={onChangeUserFile} />
            <FileUploader label="系统表" file={sysFile} onChange={onChangeSysFile} />
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-700">
            第二步：选择 Sheet {loadingSheets && <span className="text-xs text-slate-400 ml-2">读取中…</span>}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SheetSelector
              label="用户表 Sheet"
              sheets={userSheets}
              value={userSheet}
              onChange={setUserSheet}
            />
            <SheetSelector
              label="系统表 Sheet"
              sheets={sysSheets}
              value={sysSheet}
              onChange={setSysSheet}
            />
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-700">第三步：输入转换规则</h2>
          <RuleEditor value={rules} onChange={setRules} />
        </section>

        <section>
          <ExecuteButton
            onClick={handleExecute}
            disabled={!canExecute}
            executing={executing}
          />
        </section>

        {error && (
          <div className="px-4 py-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {error}
          </div>
        )}

        {result && (
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-700">执行结果</h2>
            <ResultPanel result={result} />
          </section>
        )}
      </main>
    </div>
  );
}
