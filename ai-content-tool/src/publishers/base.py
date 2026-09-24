"""Common interface every platform publisher implements.

Only YouTube is fully implemented here (it has a stable, public,
well-documented upload API). Other short-video platforms (TikTok,
Instagram Reels/Facebook, Bilibili, Douyin...) either require a business/
developer application review before granting upload access, or have no
public personal-upload API at all. To add one: implement this interface,
following that platform's own official API docs and developer terms.
Do not attempt to automate uploads through a platform's private/undocumented
endpoints or by scripting the web UI - that violates most platforms' ToS.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PublishResult:
    platform: str
    remote_id: str
    url: str


class Publisher(ABC):
    name: str = "base"

    @abstractmethod
    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        thumbnail_path: Path | None = None,
    ) -> PublishResult:
        ...
