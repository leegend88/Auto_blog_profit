from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from urllib import parse, request
from urllib.error import HTTPError, URLError

from autoblog.config import AppConfig


@dataclass(frozen=True)
class BloggerDraftPayload:
    title: str
    content_html: str
    labels: tuple[str, ...]
    is_draft: bool = True


def build_draft_payload(title: str, content_html: str, labels: list[str]) -> BloggerDraftPayload:
    return BloggerDraftPayload(
        title=title.strip(),
        content_html=content_html.strip(),
        labels=tuple(label.strip() for label in labels if label.strip()),
        is_draft=True,
    )


@dataclass(frozen=True)
class BloggerPublishResult:
    post_id: str
    title: str
    url: str
    status: str
    published: str
    raw: dict[str, object]


class BloggerPublisherError(RuntimeError):
    """Raised when Blogger publishing fails."""


class BloggerPublisher:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    POSTS_URL_TEMPLATE = "https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"

    def __init__(self, config: AppConfig, timeout_seconds: int = 30) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds

    def publish_draft(self, payload: BloggerDraftPayload) -> BloggerPublishResult:
        self._validate_credentials()
        access_token = self._fetch_access_token()
        response = self._insert_post(access_token, payload)
        return BloggerPublishResult(
            post_id=str(response.get("id", "")),
            title=str(response.get("title", "")),
            url=str(response.get("url", "")),
            status=str(response.get("status", "DRAFT")),
            published=str(response.get("published", "")),
            raw=response,
        )

    def list_blogs(self) -> list[dict[str, object]]:
        self._validate_oauth_credentials()
        access_token = self._fetch_access_token()
        req = request.Request(
            "https://www.googleapis.com/blogger/v3/users/self/blogs",
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        response = self._send_request(req, "blog listing")
        items = response.get("items", [])
        return items if isinstance(items, list) else []

    def list_recent_post_titles(self, max_results: int = 20) -> list[str]:
        self._validate_credentials()
        access_token = self._fetch_access_token()
        url = (
            self.POSTS_URL_TEMPLATE.format(blog_id=self.config.blogger_blog_id)
            + f"?status=LIVE&status=DRAFT&maxResults={max_results}&fetchBodies=false"
        )
        req = request.Request(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            method="GET",
        )
        response = self._send_request(req, "recent post listing")
        items = response.get("items", [])
        if not isinstance(items, list):
            return []
        titles: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if isinstance(title, str) and title.strip():
                titles.append(title)
        return titles

    def publish_post(
        self, post_id: str, publish_date: datetime | None = None
    ) -> BloggerPublishResult:
        self._validate_credentials()
        access_token = self._fetch_access_token()
        query = ""
        if publish_date is not None:
            query = "?publishDate=" + parse.quote(publish_date.isoformat())
        url = (
            self.POSTS_URL_TEMPLATE.format(blog_id=self.config.blogger_blog_id)
            + f"/{post_id}/publish{query}"
        )
        req = request.Request(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            method="POST",
        )
        response = self._send_request(req, "publish post")
        return BloggerPublishResult(
            post_id=str(response.get("id", "")),
            title=str(response.get("title", "")),
            url=str(response.get("url", "")),
            status=str(response.get("status", "LIVE")),
            published=str(response.get("published", "")),
            raw=response,
        )

    def _validate_credentials(self) -> None:
        missing = self._missing_oauth_fields()
        if not self.config.blogger_blog_id:
            missing.append("BLOGGER_BLOG_ID")
        if missing:
            raise BloggerPublisherError(
                "Missing required Blogger credentials in env file: "
                + ", ".join(missing)
            )

    def _validate_oauth_credentials(self) -> None:
        missing = self._missing_oauth_fields()
        if missing:
            raise BloggerPublisherError(
                "Missing required Blogger OAuth credentials in env file: "
                + ", ".join(missing)
            )

    def _missing_oauth_fields(self) -> list[str]:
        missing = []
        if not self.config.google_client_id:
            missing.append("GOOGLE_CLIENT_ID")
        if not self.config.google_client_secret:
            missing.append("GOOGLE_CLIENT_SECRET")
        if not self.config.google_refresh_token:
            missing.append("GOOGLE_REFRESH_TOKEN")
        return missing

    def _fetch_access_token(self) -> str:
        token_request = parse.urlencode(
            {
                "client_id": self.config.google_client_id,
                "client_secret": self.config.google_client_secret,
                "refresh_token": self.config.google_refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        req = request.Request(
            self.TOKEN_URL,
            data=token_request,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        response = self._send_request(req, "token exchange")
        access_token = response.get("access_token")
        if not access_token:
            raise BloggerPublisherError("OAuth token response did not include access_token.")
        return str(access_token)

    def _insert_post(
        self, access_token: str, payload: BloggerDraftPayload
    ) -> dict[str, object]:
        url = (
            self.POSTS_URL_TEMPLATE.format(blog_id=self.config.blogger_blog_id)
            + "?isDraft=true"
        )
        body = json.dumps(
            {
                "kind": "blogger#post",
                "title": payload.title,
                "content": payload.content_html,
                "labels": list(payload.labels),
            }
        ).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._send_request(req, "draft post insert")

    def _send_request(self, req: request.Request, action: str) -> dict[str, object]:
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise BloggerPublisherError(
                f"Blogger {action} failed with HTTP {exc.code}: {details}"
            ) from exc
        except URLError as exc:
            raise BloggerPublisherError(
                f"Blogger {action} failed due to a network error: {exc.reason}"
            ) from exc
