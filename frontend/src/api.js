async function readError(resp) {
  try {
    const data = await resp.json();
    return data.detail || data.error || `HTTP ${resp.status}`;
  } catch {
    return `HTTP ${resp.status}`;
  }
}

export async function fetchSheets(userFile, sysFile) {
  const fd = new FormData();
  fd.append("user_file", userFile);
  fd.append("sys_file", sysFile);
  const resp = await fetch("/api/sheets", { method: "POST", body: fd });
  if (!resp.ok) {
    throw new Error(await readError(resp));
  }
  return resp.json();
}

export async function executeMapping({
  userFile,
  sysFile,
  userSheet,
  sysSheet,
  rules,
}) {
  const fd = new FormData();
  fd.append("user_file", userFile);
  fd.append("sys_file", sysFile);
  fd.append("user_sheet", userSheet);
  fd.append("sys_sheet", sysSheet);
  fd.append("rules", rules);

  const resp = await fetch("/api/execute", { method: "POST", body: fd });
  if (!resp.ok) {
    throw new Error(await readError(resp));
  }
  const blob = await resp.blob();
  const downloadUrl = URL.createObjectURL(blob);

  const logHeader = resp.headers.get("X-Execute-Log") || "";
  let log = null;
  try {
    log = JSON.parse(decodeURIComponent(logHeader));
  } catch {
    log = { warnings: ["未能解析执行日志"] };
  }
  return { downloadUrl, log };
}
