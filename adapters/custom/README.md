# 自訂 Adapter

在此目錄建立你自己的 YAML Adapter，格式請參考 `../builtin/twitter.yaml`。

## YAML 格式說明

```yaml
name: 網站名稱
domains:
  - 網域\.com   # 支援正規表示式

actions:
  動作名稱:
    - type: click | fill | press | wait | wait_for_selector
      selector: "CSS Selector"
      text: "{{text}}"   # 文字動作中用 {{text}} 代表傳入的文字
      wait_ms: 500
      key: Enter         # type: press 時使用
```

## 支援的動作類型

| type | 說明 |
|------|------|
| `click` | 點擊元素 |
| `fill` | 在輸入框填入文字 |
| `press` | 按鍵盤按鍵 |
| `wait` | 等待指定毫秒 |
| `wait_for_selector` | 等待元素出現 |

## 支援的社群操作

- `like` - 按讚
- `unlike` - 取消按讚
- `reply` - 回覆（需要 text 參數）
- `post` - 發佈新貼文（需要 text 參數）
- `repost` - 轉發
- `bookmark` - 收藏
- `follow` - 追蹤
- `unfollow` - 取消追蹤
