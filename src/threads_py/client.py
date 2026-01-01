"""Typed client scaffold for inferred Threads operations."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict, cast

import httpx

# Type aliases for media types
SimpleMediaType = Literal["TEXT", "IMAGE", "VIDEO"]
UnitMediaType = Literal["IMAGE", "VIDEO"]
class Paging(TypedDict, total=False):
    """Pagination info for fetching next page of results."""
    previous: Optional[str]
    next: Optional[str]


class PagedPosts(TypedDict, total=False):
    """A page of posts with pagination metadata."""
    data: List["ThreadPost"]
    paging: Paging


class PostsPage(TypedDict, total=False):
    """A page of Post objects with pagination metadata."""
    posts: List["Post"]
    paging: Paging


class UserProfile(TypedDict, total=False):
    """User profile information from the Threads API."""
    id: str
    username: str
    name: str
    bio: Optional[str]
    followers_count: int
    following_count: int
    created_time: str


class PostMedia(TypedDict, total=False):
    """Media attached to a post (image, video, or GIF)."""
    id: str
    media_type: Literal["image", "video", "gif"]
    url: str
    thumbnail_url: Optional[str]


class ThreadPost(TypedDict, total=False):
    """A published Threads post with metadata and engagement metrics."""
    id: str
    text: str
    author_id: str
    created_time: str
    reply_to_id: Optional[str]
    media: List[PostMedia]
    like_count: int
    repost_count: int
    quote_count: int
    reply_count: int
    visibility: Optional[str]
    link_attachment_url: Optional[str]


class PostActionResult(TypedDict, total=False):
    """Result of a post action (like, unlike, repost, etc.)."""
    id: str
    success: bool


class RelationshipResult(TypedDict, total=False):
    """Result of a follow/unfollow action."""
    user_id: str
    following: bool


class SubscriptionResult(TypedDict, total=False):
    """Result of webhook subscription."""
    id: str
    callback_url: str
    verify_token: str
    status: str


class SearchResult(TypedDict, total=False):
    """A search result (user or post)."""
    id: str
    type: Literal["user", "post"]
    text: Optional[str]
    username: Optional[str]
    name: Optional[str]


class MediaContainerResponse(TypedDict):
    """Response from creating a media container."""
    id: str


class PublishResponse(TypedDict):
    """Response from publishing a media container."""
    id: str


class GifAttachment(TypedDict):
    """A GIF attachment for a post."""
    gif_id: str
    provider: Literal["TENOR"]

RETRY_COUNT = 3  # Number of retries for media container creation
RETRY_DELAY = 3  # Delay in seconds between retries

class PublishedPost:
    """A published Threads post with methods for interactions and accessing parent post.
    
    Attributes:
        parent: The parent post if this is a reply, otherwise None
    """

    def __init__(self, client: "ThreadsClient", data: ThreadPost):
        self._client = client
        self._data = data
        self.parent: Optional["PublishedPost"] = None  # Set when replying
    @property
    def id(self) -> str:
        """Get the unique post ID."""
        return self._data.get("id", "")

    @property
    def data(self) -> ThreadPost:
        """Get raw post data."""
        return self._data

    def refresh(self) -> PublishedPost:
        """Refresh post data from the API."""
        self._data = self._client._get_post_resource(self.id)
        return self

    def edit(self, *, text: Optional[str] = None, media_ids: Optional[List[str]] = None) -> PublishedPost:
        """Edit post text or media (if supported by API)."""
        self._data = self._client._edit_post_resource(self.id, text=text, media_ids=media_ids)
        return self

    def delete(self) -> PostActionResult:
        """Delete this post."""
        return self._client._delete_post_resource(self.id)

    def like(self) -> PostActionResult:
        """Like this post."""
        return self._client._like_post_resource(self.id)

    def unlike(self) -> PostActionResult:
        """Remove like from this post."""
        return self._client._unlike_post_resource(self.id)

    def repost(self, *, comment: Optional[str] = None) -> PostActionResult:
        """Repost this post with optional comment."""
        return self._client._repost_post_resource(self.id, comment=comment)

    def reply(
        self,
        content: "Post"
    ) -> "PublishedPost":
        """Reply to this post with the given pre-built content.
        
        Args:
            content: A Post draft to publish as a reply to this post
        
        Returns:
            PublishedPost: The published reply post
        """
        content._reply_to_id = self.id
        result = content.publish()
        result.parent = self
        return result
class CarouselPost:
    """A carousel post containing multiple media items."""
    
    def __init__(
        self,
        client: "ThreadsClient",
        *,
        media_urls: Optional[List[Tuple[UnitMediaType, str]]],
        reply_to_id: Optional[str] = None,
        text: Optional[str] = None,
        user_id: str,
        topic_tag: Optional[str] = None,
    ):
        self._client = client
        self._user_id = user_id
        self.media_urls = media_urls
        self._reply_to_id = reply_to_id
        self._text = text
        if topic_tag:
            topic_tag = topic_tag.replace(".", "").replace("&", "")[:50]
        self._topic_tag = topic_tag
    def publish(self) -> PublishedPost:
        """Publish this carousel post to Threads.
        
        Handles the two-step media container creation and publishing flow internally.
        Returns the published PublishedPost object.
        """
        container_id = ""
        for attempt in range(RETRY_COUNT):  # Retry up to 3 times
            try:
                container_id = self._client._create_carousel_container(
                    user_id=self._user_id,
                    children=self.media_urls,
                    reply_to_id=self._reply_to_id,
                    text=self._text,
                    topic_tag=self._topic_tag,
                )
            except Exception as e:
                print(f"Failed to create media container: {str(e)}")
                time.sleep(RETRY_DELAY)  # Simple retry delay
                continue
            break
        for attempt in range(RETRY_COUNT):  # Retry up to 3 times
            try:
                return self._client._publish_media_container(self._user_id, container_id)
            except Exception as e:
                print(f"Failed to publish media container: {str(e)}")
                time.sleep(RETRY_DELAY)  # Simple retry delay
                continue
        raise RuntimeError("Failed to publish carousel post after multiple attempts")
    
class Post:
    """A post draft that can be customized before publishing.
    
    Represents a post before it's published. Users build up the post with text, media,
    topic tags, etc., then call publish() to create and post it to Threads.
    """

    def __init__(
        self,
        client: "ThreadsClient",
        *,
        media_type: SimpleMediaType = "TEXT",
        text: Optional[str] = None,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        reply_to_id: Optional[str] = None,
        reply_control: Optional[str] = None,
        topic_tag: Optional[str] = None,
        link_attachment: Optional[str] = None,
        gif_attachment: Optional[GifAttachment] = None,
        is_spoiler_media: bool = False,
        user_id: str,
    ):
        self._client = client
        self._user_id = user_id
        self._media_type: SimpleMediaType = media_type
        self._text = text
        self._image_url = image_url
        self._video_url = video_url
        self._reply_to_id = reply_to_id
        self._reply_control = reply_control
        if topic_tag:
            topic_tag = topic_tag.replace(".", "").replace("&", "")[:50]
        self._topic_tag = topic_tag
        self._link_attachment = link_attachment
        self._gif_attachment = gif_attachment
        if is_spoiler_media:
            if self._media_type not in ("IMAGE", "VIDEO"):
                raise ValueError("is_spoiler_media can only be set for IMAGE or VIDEO media types")
        self._is_spoiler_media = is_spoiler_media

    def publish(self) -> PublishedPost:
        """Publish this draft post to Threads.
        
        Handles the two-step media container creation and publishing flow internally.
        Returns the published PublishedPost object.
        """
        container_id = ""
        for attempt in range(RETRY_COUNT):  # Retry up to 3 times
            try:
                container_id = self._client._create_media_container(
                    user_id=self._user_id,
                    media_type=self._media_type,
                    text=self._text,
                    image_url=self._image_url,
                    video_url=self._video_url,
                    reply_to_id=self._reply_to_id,
                    reply_control=self._reply_control,
                    topic_tag=self._topic_tag,
                    link_attachment=self._link_attachment,
                    gif_attachment=self._gif_attachment,
                    is_spoiler_media=self._is_spoiler_media,
                )
            except Exception as e:
                print(f"Failed to create media container: {str(e)}")
                time.sleep(RETRY_DELAY)  # Simple retry delay
                continue
            break
        for attempt in range(RETRY_COUNT):  # Retry up to 3 times
            try:
                return self._client._publish_media_container(self._user_id, container_id)
            except Exception as e:
                print(f"Failed to publish media container: {str(e)}")
                time.sleep(RETRY_DELAY)  # Simple retry delay
                continue
        raise RuntimeError("Failed to publish post after multiple attempts")

class ThreadsClient:
    """Typed client for the Meta Threads API.
    
    Provides methods for fetching user profiles, creating and managing posts,
    handling interactions (likes, reposts, replies), searching content, and
    managing relationships (follow/unfollow).
    
    The client handles Threads' two-step publishing flow (media container creation
    and publishing) internally, so users just call create_post().publish().
    
    Args:
        access_token: Your Threads API access token
        user_id: Optional default user ID for convenience (can override in individual methods)
        base_url: API base URL (default: https://graph.threads.net)
        timeout: HTTP request timeout in seconds (default: 10)
    
    Example:
        with ThreadsClient(access_token) as client:
            post_draft = client.create_post(user_id, text="Hello Threads!")
            published = post_draft.publish()
            published.like()
    """

    def __init__(
        self,
        access_token: str,
        user_id: str,
        *,
        base_url: str = "https://graph.threads.net",
        timeout: float = 10.0,
    ) -> None:
        self.access_token = access_token
        self.user_id = user_id
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout, headers={"Authorization": f"Bearer {access_token}"})

    def close(self) -> None:
        self._client.close()
    def get_long_lived_access_token(self, access_token: str, client_secret: str) -> str:
        """Get a long-lived access token.
        
        Args:
            access_token: The access token used for getting a long-lived token
            client_secret: The client secret required for extending the token
        Returns:
            str: The long-lived access token
        """
        token = access_token or self.access_token
        if not token:
            raise ValueError("access_token must be provided or set on client")
        
        params = {
            "grant_type": "th_extend_token",
            "access_token": token,
            "client_secret": client_secret
        }
        data = self._request_json("GET", "/access_token", params=params)
        
        long_lived_token = data.get("access_token")
        if not long_lived_token:
            raise RuntimeError("No access_token in extend response")
        
        return long_lived_token

    def refresh_access_token(self, access_token: Optional[str] = None) -> str:
        """Refresh a long-lived token.
        
        Args:
            access_token: The access token to refresh (uses self.access_token if not provided)
        
        Returns:
            str: The long-lived access token
        """
        token = access_token or self.access_token
        if not token:
            raise ValueError("access_token must be provided or set on client")
        
        params = {
            "grant_type": "th_refresh_token",
            "access_token": token,
        }
        data = self._request_json("GET", "/refresh_access_token", params=params)
        
        new_token = data.get("access_token")
        if not new_token:
            raise RuntimeError("No access_token in refresh response")
        
        self.access_token = new_token
        self._client.headers["Authorization"] = f"Bearer {new_token}"
        return new_token

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        print(f"Requesting {method} {url} with params={params} json={json}")
        try:
            response = self._client.request(method, url, params=params, json=json)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_msg = f"{method} {url} failed with status {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_msg += f": {error_data['error']}"
            except Exception:
                pass
            raise RuntimeError(error_msg) from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Request to {url} failed: {str(e)}") from e
        
        try:
            return cast(Dict[str, Any], response.json())
        except ValueError as e:
            raise RuntimeError(f"Failed to parse JSON response from {url}") from e

    # Low-level resource helpers (internal)
    def _get_post_resource(self, post_id: str) -> ThreadPost:
        return cast(ThreadPost, self._request_json("GET", f"/{post_id}"))

    def _create_media_container(
        self,
        user_id: str,
        *,
        media_type: SimpleMediaType = "TEXT",
        text: Optional[str] = None,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        is_carousel_item: bool = False,
        children: Optional[List[str]] = None,
        reply_to_id: Optional[str] = None,
        reply_control: Optional[str] = None,
        topic_tag: Optional[str] = None,
        link_attachment: Optional[str] = None,
        gif_attachment: Optional[GifAttachment] = None,
        is_spoiler_media: bool = False,
    ) -> str:
        """Step 1: Create a media container. Returns container ID."""
        payload: Dict[str, Any] = {"media_type": media_type}
        
        if text:
            payload["text"] = text
        if image_url:
            payload["image_url"] = image_url
        if video_url:
            payload["video_url"] = video_url
        if is_carousel_item:
            payload["is_carousel_item"] = "true"
        if children:
            payload["children"] = ",".join(children)
        if reply_to_id:
            payload["reply_to_id"] = reply_to_id
        if reply_control:
            payload["reply_control"] = reply_control
        if topic_tag:
            payload["topic_tag"] = topic_tag
        if link_attachment:
            payload["link_attachment"] = link_attachment
        if gif_attachment:
            payload["gif_attachment"] = gif_attachment
        if is_spoiler_media:
            payload["is_spoiler_media"] = "true"
        
        response = cast(MediaContainerResponse, self._request_json("POST", f"/{user_id}/threads", json=payload))
        return response["id"]

    def _publish_media_container(self, user_id: str, container_id: str) -> PublishedPost:
        """Step 2: Publish a media container."""
        payload = {"creation_id": container_id}
        response = cast(PublishResponse, self._request_json("POST", f"/{user_id}/threads_publish", json=payload))
        return PublishedPost(self, self._get_post_resource(response["id"]))

    def _create_carousel_container(
            self, 
            user_id: str, 
            *, 
            children: Optional[List[Tuple[UnitMediaType, str]]] = None, 
            reply_to_id: Optional[str] = None, 
            text: Optional[str] = None,
            topic_tag: Optional[str] = None,
            ) -> str:
        """Create a carousel media container. Returns container ID."""
        payload: Dict[str, Any] = {"media_type": "CAROUSEL"}
        media_ids: List[str] = []
        for child in children or []:
            unit = self.create_post(
                media_type=child[0],
                image_url=child[1] if child[0] == "IMAGE" else None,
                video_url=child[1] if child[0] == "VIDEO" else None
            )
            unit = self._create_media_container(
                user_id, 
                media_type=child[0], 
                is_carousel_item=True, 
                text=None, 
                image_url=child[1] if child[0] == "IMAGE" else None, 
                video_url=child[1] if child[0] == "VIDEO" else None
            )
            media_ids.append(unit)
        payload["children"] = ",".join(media_ids)
        if reply_to_id:
            payload["reply_to_id"] = reply_to_id
        if text:
            payload["text"] = text
        if topic_tag:
            payload["topic_tag"] = topic_tag
        response = cast(MediaContainerResponse, self._request_json("POST", f"/{user_id}/threads", json=payload))
        return response["id"]



    def _edit_post_resource(
        self,
        post_id: str,
        *,
        text: Optional[str] = None,
        media_ids: Optional[List[str]] = None,
    ) -> ThreadPost:
        payload: Dict[str, Any] = {}
        if text is not None:
            payload["text"] = text
        if media_ids is not None:
            payload["media_ids"] = media_ids
        return cast(ThreadPost, self._request_json("PATCH", f"/threads/{post_id}", json=payload))

    def _delete_post_resource(self, post_id: str) -> PostActionResult:
        return cast(PostActionResult, self._request_json("DELETE", f"/threads/{post_id}"))

    def _like_post_resource(self, post_id: str) -> PostActionResult:
        return cast(PostActionResult, self._request_json("POST", f"/threads/{post_id}/likes"))

    def _unlike_post_resource(self, post_id: str) -> PostActionResult:
        return cast(PostActionResult, self._request_json("DELETE", f"/threads/{post_id}/likes"))

    def _repost_post_resource(self, post_id: str, *, comment: Optional[str] = None) -> PostActionResult:
        payload: Dict[str, Any] = {"post_id": post_id}
        if comment:
            payload["comment"] = comment
        return cast(PostActionResult, self._request_json("POST", f"/threads/{post_id}/reposts", json=payload))

    # Profile
    def get_user_profile(self, user_id: str, *, fields: Optional[List[str]] = None) -> UserProfile:
        """Get a user's profile information.
        
        Args:
            user_id: The Threads user ID
            fields: Optional list of fields to retrieve
        """
        params: Dict[str, Any] | None = {"fields": ",".join(fields)} if fields else None
        return cast(UserProfile, self._request_json("GET", f"/{user_id}", params=params))

    # Posts
    def list_user_posts(self, user_id: Optional[str] = None, *, limit: int = 20, cursor: Optional[str] = None) -> PostsPage:
        """List a user's posts.
        
        Args:
            user_id: The Threads user ID (uses self.user_id if not provided)
            limit: Number of posts to retrieve (default 20)
            cursor: Pagination cursor for fetching next page
        """
        if user_id is None:
            user_id = self.user_id
        if user_id is None:
            raise ValueError("user_id must be provided or set on client")
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        raw = cast(PagedPosts, self._request_json("GET", f"/{user_id}/threads", params=params))
        posts = [PublishedPost(self, item) for item in raw.get("data", [])]
        return cast(PostsPage, {"posts": posts, "paging": raw.get("paging", {})})

    def get_post(self, post_id: str, *, fields: Optional[List[str]] = None) -> PublishedPost:
        """Fetch a published post by ID.
        
        Args:
            post_id: The post ID
            fields: Optional list of fields to retrieve
        """
        params: Dict[str, Any] | None = {"fields": ",".join(fields)} if fields else None
        return PublishedPost(self, cast(ThreadPost, self._request_json("GET", f"/{post_id}", params=params)))

    def create_post(
        self,
        text: Optional[str] = None,
        *,
        media_type: SimpleMediaType = "TEXT",
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        reply_to_id: Optional[str] = None,
        reply_control: Optional[str] = None,
        topic_tag: Optional[str] = None,
        link_attachment: Optional[str] = None,
        gif_attachment: Optional[GifAttachment] = None,
        user_id: Optional[str] = None,
    ) -> Post:
        """Create a post draft for customization before publishing.
        
        Returns a Post object that you can further customize before calling publish().
        
        Args:
            user_id: The Threads user ID (uses self.user_id if not provided)
            media_type: Type of post (TEXT, IMAGE, or VIDEO)
            text: Post text content
            image_url: URL of image (required for IMAGE posts)
            video_url: URL of video (required for VIDEO posts)
            reply_to_id: Post ID to reply to
            reply_control: Reply restrictions (everyone, mentioned_users, followers)
            topic_tag: Topic tag for the post (1-50 chars, no . or &)
            link_attachment: URL to attach as preview (TEXT only, max 5 links)
            gif_attachment: GIF to attach with gif_id and provider (Tenor)
        
        Returns:
            PrePost: A draft post ready to publish
        
        Example:
            draft = client.create_post(text="Hello Threads!")
            published = draft.publish()
        """
        if user_id is None:
            user_id = self.user_id
        if user_id is None:
            raise ValueError("user_id must be provided or set on client")
        return Post(
            self,
            media_type=media_type,
            text=text,
            image_url=image_url,
            video_url=video_url,
            reply_to_id=reply_to_id,
            reply_control=reply_control,
            topic_tag=topic_tag,
            link_attachment=link_attachment,
            gif_attachment=gif_attachment,
            user_id=user_id,
        )
    def create_carousel_post(
        self,
        *,
        media_urls: Optional[List[Tuple[UnitMediaType, str]]],
        reply_to_id: Optional[str] = None,
        user_id: Optional[str] = None,
        text: Optional[str] = None,
    ) -> CarouselPost:
        """Create a carousel post draft for customization before publishing.
        
        Returns a CarouselPost object that you can further customize before calling publish().
        
        Args:
            user_id: The Threads user ID (uses self.user_id if not provided)
            media_urls: List of tuples with media type and URL for each item in the carousel
            reply_to_id: Post ID to reply to
        """
        if user_id is None:
            user_id = self.user_id
        if user_id is None:
            raise ValueError("user_id must be provided or set on client")
        return CarouselPost(
            self,
            media_urls=media_urls,
            reply_to_id=reply_to_id,
            user_id=user_id,
            text=text,
        )
    # Relationships
    def follow_user(self, target_user_id: str) -> RelationshipResult:
        """Follow a user.
        
        Args:
            target_user_id: The user ID to follow
        """
        return cast(RelationshipResult, self._request_json("POST", f"/{target_user_id}/follow"))

    def unfollow_user(self, target_user_id: str) -> RelationshipResult:
        """Unfollow a user.
        
        Args:
            target_user_id: The user ID to unfollow
        """
        return cast(RelationshipResult, self._request_json("DELETE", f"/{target_user_id}/follow"))

    # Search
    def search(
        self,
        query: str,
        *,
        search_type: Literal["posts", "users"] = "posts",
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for posts or users.
        
        Args:
            query: Search query string
            search_type: Type of search (posts or users)
            limit: Number of results (default 20)
            cursor: Pagination cursor
        """
        params: Dict[str, Any] = {"q": query, "type": search_type, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request_json("GET", "/search", params=params)

    # Webhooks / subscriptions
    def subscribe_webhook(
        self,
        callback_url: str,
        *,
        verify_token: str,
        fields: Optional[List[str]] = None,
    ) -> SubscriptionResult:
        """Subscribe to webhook events.
        
        Args:
            callback_url: URL to receive webhook events
            verify_token: Token for verifying webhook requests
            fields: Event fields to subscribe to
        """
        payload: Dict[str, Any] = {"callback_url": callback_url, "verify_token": verify_token}
        if fields:
            payload["fields"] = fields
        return cast(SubscriptionResult, self._request_json("POST", "/webhooks", json=payload))

    def __enter__(self) -> "ThreadsClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001,N803,N806
        self.close()
