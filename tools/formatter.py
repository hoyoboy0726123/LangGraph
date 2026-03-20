"""
Formatter：將資料格式化為 table / json / yaml / md / csv。
（工具函式，非 LangChain tool，供其他模組直接呼叫）
"""
import json
import csv
import io
from typing import Any


def format_output(data: Any, fmt: str = "md") -> str:
    """
    將資料格式化輸出。

    Args:
        data: 任意資料（str / list / dict）
        fmt: 輸出格式 table | json | yaml | md | csv

    Returns:
        格式化後的字串
    """
    fmt = fmt.lower().strip()

    if fmt == "json":
        return _to_json(data)
    elif fmt == "yaml":
        return _to_yaml(data)
    elif fmt == "csv":
        return _to_csv(data)
    elif fmt == "table":
        return _to_table(data)
    else:
        return _to_md(data)


def _to_json(data: Any) -> str:
    if isinstance(data, str):
        return data
    return json.dumps(data, ensure_ascii=False, indent=2)


def _to_yaml(data: Any) -> str:
    try:
        import yaml
        if isinstance(data, str):
            return data
        return yaml.dump(data, allow_unicode=True, default_flow_style=False)
    except ImportError:
        return _to_json(data)


def _to_csv(data: Any) -> str:
    if isinstance(data, str):
        return data

    output = io.StringIO()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    elif isinstance(data, list):
        writer = csv.writer(output)
        for row in data:
            writer.writerow([row] if not isinstance(row, (list, tuple)) else row)
    else:
        writer = csv.writer(output)
        if isinstance(data, dict):
            for k, v in data.items():
                writer.writerow([k, v])

    return output.getvalue()


def _to_table(data: Any) -> str:
    if isinstance(data, str):
        return data

    try:
        from tabulate import tabulate
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return tabulate(data, headers="keys", tablefmt="github")
        elif isinstance(data, dict):
            return tabulate(data.items(), headers=["Key", "Value"], tablefmt="github")
        return str(data)
    except ImportError:
        return _to_md(data)


def _to_md(data: Any) -> str:
    if isinstance(data, str):
        return data

    if isinstance(data, list):
        lines = []
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                lines.append(f"### 項目 {i}")
                for k, v in item.items():
                    lines.append(f"- **{k}**：{v}")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)

    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            lines.append(f"- **{k}**：{v}")
        return "\n".join(lines)

    return str(data)
