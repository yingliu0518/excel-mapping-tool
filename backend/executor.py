from typing import Any

import pandas as pd
from openpyxl import Workbook

from compute import COMPUTE_FUNCTIONS


def _apply_filters(user_df: pd.DataFrame, filters: list[dict], warnings: list[str]) -> pd.DataFrame:
    df = user_df.copy()
    for f in filters or []:
        col = f.get("column")
        op = f.get("operator")
        val = f.get("value")
        if col is None or col not in df.columns:
            warnings.append(f"筛选跳过：用户表中不存在列「{col}」")
            continue
        col_data = df[col].astype(str)
        target = "" if val is None else str(val)
        if op == "equals":
            df = df[col_data == target]
        elif op == "contains":
            df = df[col_data.str.contains(target, na=False, regex=False)]
        elif op == "not_equals":
            df = df[col_data != target]
        else:
            warnings.append(f"筛选跳过：未知运算符「{op}」")
    return df


def _set_cell(ws, row_num: int, headers: list[str], col_name: str, value: Any, warnings: list[str]) -> bool:
    if col_name is None or col_name not in headers:
        warnings.append(f"系统表中不存在列「{col_name}」，跳过")
        return False
    col_idx = headers.index(col_name)
    if isinstance(value, float) and pd.isna(value):
        value = ""
    ws.cell(row=row_num, column=col_idx + 1).value = value
    return True


def execute_mapping(
    config: dict,
    user_df: pd.DataFrame,
    sys_wb: Workbook,
    sys_sheet: str,
) -> tuple[Workbook, dict]:
    warnings: list[str] = []

    if sys_sheet not in sys_wb.sheetnames:
        raise ValueError(f"系统表中不存在 Sheet「{sys_sheet}」")
    ws = sys_wb[sys_sheet]

    headers = [cell.value for cell in ws[1]]

    key_mapping = config.get("key_mapping") or {}
    user_key_col = key_mapping.get("user_col")
    sys_key_col = key_mapping.get("sys_col")
    if not user_key_col or not sys_key_col:
        raise ValueError("缺少主键声明 (key_mapping)")
    if user_key_col not in user_df.columns:
        raise ValueError(f"用户表中不存在主键列「{user_key_col}」")
    if sys_key_col not in headers:
        raise ValueError(f"系统表中不存在主键列「{sys_key_col}」")

    sys_key_idx = headers.index(sys_key_col)

    sys_index: dict[str, int] = {}
    for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
        key_val = row[sys_key_idx].value
        if key_val is None:
            continue
        key_str = str(key_val).strip()
        if key_str:
            sys_index[key_str] = row_num

    filtered_df = _apply_filters(user_df, config.get("filters") or [], warnings)
    filtered_count = len(filtered_df)

    updated_count = 0
    skipped_keys: list[str] = []
    mappings = config.get("mappings") or []

    for _, user_row in filtered_df.iterrows():
        raw_key = user_row.get(user_key_col)
        if raw_key is None or (isinstance(raw_key, float) and pd.isna(raw_key)):
            skipped_keys.append("")
            continue
        key_val = str(raw_key).strip()
        row_num = sys_index.get(key_val)
        if row_num is None:
            skipped_keys.append(key_val)
            continue

        for mapping in mappings:
            mtype = mapping.get("type")

            if mtype == "copy":
                src_col = mapping.get("source_column")
                tgt_col = mapping.get("target_column")
                if src_col is None or src_col not in user_df.columns:
                    warnings.append(f"copy 跳过：用户表中不存在列「{src_col}」")
                    continue
                _set_cell(ws, row_num, headers, tgt_col, user_row.get(src_col), warnings)

            elif mtype == "conditional":
                src_col = mapping.get("source_column")
                if src_col is None or src_col not in user_df.columns:
                    warnings.append(f"conditional 跳过：用户表中不存在列「{src_col}」")
                    continue
                src_val_raw = user_row.get(src_col)
                src_val = "" if src_val_raw is None or (isinstance(src_val_raw, float) and pd.isna(src_val_raw)) else str(src_val_raw)
                matched = False
                for cond in mapping.get("conditions") or []:
                    op = cond.get("operator")
                    cval = cond.get("value")
                    hit = False
                    if op == "equals":
                        hit = src_val == ("" if cval is None else str(cval))
                    elif op == "contains":
                        hit = ("" if cval is None else str(cval)) in src_val
                    elif op == "not_equals":
                        hit = src_val != ("" if cval is None else str(cval))
                    elif op == "in":
                        cand = cval if isinstance(cval, list) else [cval]
                        hit = src_val in [("" if c is None else str(c)) for c in cand]
                    if hit:
                        _set_cell(ws, row_num, headers, cond.get("target_column"), cond.get("target_value"), warnings)
                        matched = True
                        break
                if not matched:
                    default = mapping.get("default")
                    if default:
                        _set_cell(ws, row_num, headers, default.get("target_column"), default.get("target_value"), warnings)

            elif mtype == "compute":
                fn_name = mapping.get("function")
                fn = COMPUTE_FUNCTIONS.get(fn_name)
                if fn is None:
                    warnings.append(f"compute 跳过：未知函数「{fn_name}」")
                    continue
                src_cols = mapping.get("source_columns") or []
                missing = [c for c in src_cols if c not in user_df.columns]
                if missing:
                    warnings.append(f"compute 跳过：用户表中不存在列 {missing}")
                    continue
                result = fn(user_row, src_cols)
                _set_cell(ws, row_num, headers, mapping.get("target_column"), result, warnings)

            else:
                warnings.append(f"未知 mapping 类型：{mtype}")

        updated_count += 1

    log = {
        "filtered_count": filtered_count,
        "updated_count": updated_count,
        "skipped_count": len(skipped_keys),
        "skipped_keys": skipped_keys,
        "warnings": warnings,
        "config": config,
    }
    return sys_wb, log
