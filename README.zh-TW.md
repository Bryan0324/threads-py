# threads-py

一個簡潔的 Python 套件，用於 Meta Threads API。目前提供最小化的客戶端；根據您的應用需求擴展端點。

## 介紹

**threads-py** 是一個非官方的 Python 包裝器，為 Meta Threads API 提供方便的客户端界面。它隱藏了 Threads 複雜的兩步發佈流程（媒體容器創建 → 發佈），讓您可以專注於內容創建。

### 主要特性

- **直觀的草稿模式**：`create_post()` 返回一個草稿 `Post` 物件，調用 `.publish()` 時才發佈
- **物件導向設計**：與 `PublishedPost` 物件交互，而不是原始 ID
- **完整的媒體支持**：支持文本、圖片、視頻、輪播貼文和 GIF
- **回覆功能**：輕鬆回覆貼文並訪問父貼文引用
- **類型提示**：使用 TypedDict 提供完整的類型檢查和 IDE 支持
- **自動重試**：內置重試邏輯處理媒體容器創建失敗
- **錯誤處理**：詳細的錯誤消息和異常追踪

## 安裝

```bash
pip install threads-py
```

## 快速開始

```python
from meta_threads import ThreadsClient

access_token = "YOUR_ACCESS_TOKEN"
user_id = "YOUR_USER_ID"

# 使用上下文管理器確保資源清理
with ThreadsClient(access_token, user_id=user_id) as client:
    # 獲取用戶個人資料
    me = client.get_user_profile(user_id)
    print(f"用戶名: {me.get('username')}")

    # 創建並發佈文本貼文
    draft = client.create_post(text="你好，Threads！")
    published = draft.publish()
    
    # 與貼文互動
    published.like()
    published.edit(text="更新的文本")

    # 回覆貼文
    reply_draft = client.create_post(text="感謝閱讀")
    reply = published.reply(reply_draft)
    
    # 訪問父貼文
    if reply.parent:
        print(f"回覆給: {reply.parent.id}")

    # 創建圖片貼文，帶主題標籤
    image_draft = client.create_post(
        media_type="IMAGE",
        text="看看這張圖片！",
        image_url="https://example.com/image.jpg",
        topic_tag="攝影",
    )
    image_post = image_draft.publish()

    # 創建輪播貼文
    carousel = client.create_carousel_post(
        media_urls=[
            ("IMAGE", "https://example.com/1.jpg"),
            ("IMAGE", "https://example.com/2.jpg"),
        ],
        text="我的輪播貼文",
    )
    carousel_post = carousel.publish()

    # 列出用戶貼文
    page = client.list_user_posts()
    for p in page.get("posts", []):
        print(f"貼文 ID: {p.id}")
```

## 高級用法

### 獲取長期訪問令牌

```python
# 獲取初始的長期令牌
long_lived_token = client.get_long_lived_access_token(
    access_token="short_lived_token",
    client_secret="your_client_secret"
)

# 刷新現有的長期令牌
refreshed_token = client.refresh_access_token()
```

### 自定義媒體

```python
# 創建視頻貼文
video_draft = client.create_post(
    media_type="VIDEO",
    text="查看我的視頻",
    video_url="https://example.com/video.mp4",
)
video_post = video_draft.publish()

# 添加 GIF 附件
gif_draft = client.create_post(
    text="有趣的 GIF",
    gif_attachment={"gif_id": "tenor_id", "provider": "TENOR"},
)
gif_post = gif_draft.publish()

# 添加鏈接附件
link_draft = client.create_post(
    text="查看這個鏈接",
    link_attachment="https://example.com",
)
link_post = link_draft.publish()
```

### 管理貼文

```python
# 刷新貼文數據
published.refresh()

# 刪除貼文
published.delete()

# 重新發佈
published.repost(comment="太棒了！")
```

## 注意事項

- **發佈流程**：發佈由 Threads API 在內部自動處理（兩步流程：媒體容器創建 → 發佈）
- **媒體類型**：支持 TEXT、IMAGE、VIDEO 和 CAROUSEL
- **主題標籤**：自動清理特殊字符（`.` 和 `&`）並限制為 50 個字符
- **輪播貼文**：需要 2-20 個項目，計為單個貼文以應對速率限制
- **重試邏輯**：默認重試 3 次，延遲 3 秒，用於媒體容器創建失敗
- **HTTP 客戶端**：使用 `httpx` 進行請求；所有非 2xx 響應都會引發異常
- **基礎 URL**：默認為 `https://graph.threads.net`

## API 參考

### ThreadsClient

主要客戶端類，提供以下方法：

- `get_user_profile(user_id, fields=None)` - 獲取用戶信息
- `get_post(post_id, fields=None)` - 獲取單個貼文
- `list_user_posts(user_id=None, limit=20, cursor=None)` - 列出用戶貼文
- `create_post(text=None, media_type="TEXT", ...)` - 創建貼文草稿
- `create_carousel_post(media_urls, ...)` - 創建輪播貼文草稿
- `follow_user(target_user_id)` - 關注用戶
- `unfollow_user(target_user_id)` - 取消關注用戶
- `search(query, search_type="posts", limit=20)` - 搜索貼文或用戶

### Post（草稿）

在發佈前自定義的貼文物件：

- `publish()` - 發佈到 Threads

### PublishedPost（已發佈）

已發佈的貼文物件，支持互動：

- `refresh()` - 從 API 刷新數據
- `edit(text=None, media_ids=None)` - 編輯貼文
- `delete()` - 刪除貼文
- `like()` - 點讚
- `unlike()` - 取消點讚
- `repost(comment=None)` - 重新發佈
- `reply(content)` - 回覆貼文

## 許可證

MIT

## 貢獻

歡迎提交問題和拉取請求！

---

**更多信息**：訪問 [英文 README](README.md) 或 [GitHub 倉庫](https://github.com/grass-cat/threads-py)
