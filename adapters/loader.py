"""
Adapter Loader：根據當前 URL 載入對應的網站 Adapter。
Adapter 定義各網站的社群操作選擇器（按讚、回覆、發文等）。

Adapter 可以是：
  - YAML 設定檔（放在 adapters/builtin/ 或 adapters/custom/）
  - Python 類別（繼承 BaseAdapter）
"""
import re
from pathlib import Path
from typing import Optional
import yaml

BUILTIN_DIR = Path(__file__).parent / "builtin"
CUSTOM_DIR = Path(__file__).parent / "custom"


class BaseAdapter:
    """所有 Adapter 的基底類別"""
    domain_patterns: list[str] = []

    def match(self, url: str) -> bool:
        return any(re.search(p, url) for p in self.domain_patterns)

    async def execute(self, page, action: str, **kwargs) -> str:
        raise NotImplementedError


class YamlAdapter(BaseAdapter):
    """從 YAML 設定檔載入的 Adapter"""

    def __init__(self, config: dict):
        self.config = config
        self.domain_patterns = config.get("domains", [])
        self.actions = config.get("actions", {})
        self.name = config.get("name", "unknown")

    async def execute(self, page, action: str, **kwargs) -> str:
        action_cfg = self.actions.get(action)
        if not action_cfg:
            return f"Adapter [{self.name}] 不支援操作：{action}"

        steps = action_cfg if isinstance(action_cfg, list) else [action_cfg]
        results = []

        for step in steps:
            step_type = step.get("type", "click")
            selector = step.get("selector", "")
            text = kwargs.get("text", step.get("text", ""))
            wait = step.get("wait_ms", 500)

            try:
                if step_type == "click":
                    await page.click(selector, timeout=10000)
                    results.append(f"✓ clicked {selector}")

                elif step_type == "fill":
                    await page.fill(selector, text, timeout=10000)
                    results.append(f"✓ filled {selector}")

                elif step_type == "press":
                    key = step.get("key", "Enter")
                    await page.keyboard.press(key)
                    results.append(f"✓ pressed {key}")

                elif step_type == "wait":
                    import asyncio
                    await asyncio.sleep(wait / 1000)
                    results.append(f"✓ waited {wait}ms")

                elif step_type == "wait_for_selector":
                    await page.wait_for_selector(selector, timeout=10000)
                    results.append(f"✓ selector appeared: {selector}")

            except Exception as e:
                results.append(f"✗ step failed: {e}")
                break

        return f"[{self.name}] {action} 執行結果：\n" + "\n".join(results)


def _load_yaml_adapters() -> list[YamlAdapter]:
    adapters = []
    for d in [BUILTIN_DIR, CUSTOM_DIR]:
        for yaml_file in d.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    if config:
                        adapters.append(YamlAdapter(config))
            except Exception as e:
                print(f"[Adapter] 載入失敗 {yaml_file}：{e}")
    return adapters


_adapters: Optional[list[BaseAdapter]] = None


def _get_all_adapters() -> list[BaseAdapter]:
    global _adapters
    if _adapters is None:
        _adapters = _load_yaml_adapters()
    return _adapters


def get_adapter_for_url(url: str) -> Optional[BaseAdapter]:
    """根據 URL 找出對應的 Adapter"""
    for adapter in _get_all_adapters():
        if adapter.match(url):
            return adapter
    return None


def reload_adapters():
    """重新載入所有 Adapter（熱更新）"""
    global _adapters
    _adapters = None
