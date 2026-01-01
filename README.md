# threads-py

A tiny Python scaffold for the Meta Threads API. Currently ships a minimal client; extend with the endpoints your app needs.

## Installation

```bash
pip install threads-py
```

## Usage

```python
from threads_py import ThreadsClient

access_token = "YOUR_TOKEN"
user_id = "YOUR_USER_ID"

# Optionally set default user_id on the client
with ThreadsClient(access_token, user_id=user_id) as client:
    # Get user profile
    me = client.get_user_profile(user_id)

    # Create a draft post then publish
    draft = client.create_post(text="Hello Threads!")
    published = draft.publish()
    published.like()
    published.edit(text="Updated text")

    # Reply to a post: build a draft, then reply()
    reply_draft = client.create_post(text="Thanks for reading")
    reply = published.reply(reply_draft)

    # Access parent post from a reply
    if reply.parent:
        print(f"Replying to: {reply.parent.id}")

    # Create an image post with topic tag
    image_draft = client.create_post(
        text="Check out this image!",
        image_url="https://example.com/image.jpg",
        topic_tag="Photography",
    )
    image_post = image_draft.publish()

    # Create a carousel post
    carousel_post = client.create_carousel(
        media_urls=[
            ("IMAGE", "https://http.cat/404.jpg"), 
            ("IMAGE", "https://http.cat/502.jpg"), 
            ("IMAGE", "https://http.cat/100.jpg")
            ],
        text="My carousel post",
    )

    # List user posts
    page = client.list_user_posts()
    for p in page.get("posts", []):
        print(p.id)
```

## Notes

- Publishing is handled automatically (uses Threads' two-step flow internally).
- Supports TEXT, IMAGE, VIDEO, and CAROUSEL media types.
- Includes topic tags, link attachments, and GIF support (Tenor).
- Uses `httpx` under the hood; raises for non-2xx responses.
- Base URL defaults to `https://graph.threads.net`.
- Carousels require 2-20 items and count as a single post against rate limits.
