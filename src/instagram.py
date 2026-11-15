"""Publish hadith image cards to Instagram without keeping them anywhere.

The Instagram API only accepts a public image URL, never an upload. So the
cards are pushed to a throwaway orphan branch of this (public) repo, Instagram
fetches them via raw.githubusercontent.com, and the branch is deleted again.
The cards never touch main or its history, and nothing is written to the
working tree.
"""

import base64
import contextlib
import os
import subprocess
import tempfile
import time
import uuid

import requests

from src.hadith_image import clean_text, render_hadith_images, to_jpeg
from src.model import Hadith
from src.utils import ensure_env_var, get_optional_env_var

GRAPH_API_URL = "https://graph.facebook.com/v23.0"
CAPTION_LIMIT = 2200
HASHTAGS = "#hadith #sunnah #islam #bukhari"
POLL_SECONDS = 3
POLL_TIMEOUT = 120


def _call(method: str, path: str, token: str, **kwargs) -> dict:
    resp = requests.request(
        method,
        f"{GRAPH_API_URL}/{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
        **kwargs,
    )
    if not resp.ok:
        # raise_for_status hides Meta's error message, which is the useful bit
        raise RuntimeError(f"{method} {path} failed: {resp.text}")
    return resp.json()


def make_caption(hadith: Hadith) -> str:
    reference = (
        f"{hadith.collection}, Hadith {hadith.hadith_no} "
        f"(Book {hadith.book_no}: {hadith.book_en})"
    )
    caption = "\n\n".join(
        [
            clean_text(hadith.narrator_en),
            clean_text(hadith.body_en),
            reference,
            HASHTAGS,
        ]
    )
    if len(caption) <= CAPTION_LIMIT:
        return caption
    # Hashtags and reference matter more than the tail of the text
    tail = f"\n\n{reference}\n\n{HASHTAGS}"
    return caption[: CAPTION_LIMIT - len(tail) - 1] + "…" + tail


def _git(cwd: str, *args: str, auth: bool = False):
    cmd = ["git"]
    if auth:
        # Header auth keeps the token out of URLs and therefore out of logs
        basic = base64.b64encode(
            f"x-access-token:{ensure_env_var('GITHUB_TOKEN')}".encode()
        ).decode()
        cmd += ["-c", f"http.extraheader=AUTHORIZATION: basic {basic}"]
    subprocess.run(cmd + list(args), cwd=cwd, check=True, capture_output=True)


def _wait_until_public(urls: list[str]):
    """Block until every URL serves an image, so Instagram doesn't hit a 404."""
    deadline = time.monotonic() + POLL_TIMEOUT
    for url in urls:
        while True:
            try:
                resp = requests.head(url, timeout=10, allow_redirects=True)
                if resp.ok and resp.headers.get("content-type", "").startswith(
                    "image/"
                ):
                    break
                status = resp.status_code
            except requests.RequestException as e:
                status = e
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{url} not public yet: {status}")
            time.sleep(POLL_SECONDS)


@contextlib.contextmanager
def temp_public_urls(jpegs: list[bytes]):
    """Yield public URLs for the images, valid only inside the block.

    Uses a fresh repo in a temp dir so the checked-out repo (and the later
    "git add ." in the commit script) never sees the images.
    """
    repo = ensure_env_var("GITHUB_REPOSITORY")
    branch = f"ig-tmp-{uuid.uuid4().hex[:12]}"
    remote = os.getenv("GIT_REMOTE_URL") or f"https://github.com/{repo}.git"
    pushed = False
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _git(tmp, "init", "-q", "-b", branch)
            names = []
            for i, jpeg in enumerate(jpegs, 1):
                name = f"card_{i}.jpg"
                with open(os.path.join(tmp, name), "wb") as f:
                    f.write(jpeg)
                names.append(name)
            _git(tmp, "add", ".")
            _git(
                tmp,
                "-c", "user.name=ananto-bot",
                "-c", "user.email=ananto-bot@bot.ai",
                "commit", "-q", "-m", "temporary Instagram cards",
            )  # fmt: skip
            pushed = True  # even a failed push may leave a partial ref
            _git(
                tmp,
                "push",
                "-q",
                remote,
                f"HEAD:refs/heads/{branch}",
                auth=True,
            )
            base = f"https://raw.githubusercontent.com/{repo}/{branch}"
            urls = [f"{base}/{n}" for n in names]
            _wait_until_public(urls)
            yield urls
        finally:
            if pushed:
                try:
                    _git(
                        tmp,
                        "push",
                        "-q",
                        remote,
                        "--delete",
                        branch,
                        auth=True,
                    )
                except subprocess.CalledProcessError as e:
                    print(f"Could not delete branch {branch}: {e.stderr}")


def _wait_until_ready(container_id: str, token: str):
    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        status = _call(
            "GET", container_id, token, params={"fields": "status_code"}
        )["status_code"]
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container {container_id}: {status}")
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"Instagram container {container_id} not ready")


def get_token() -> str:
    """Secrets often get pasted with quotes, spaces or a 'Bearer ' prefix."""
    token = ensure_env_var("IG_ACCESS_TOKEN").strip().strip("\"'").strip()
    return token.removeprefix("Bearer ").strip()


def get_ig_user_id(token: str) -> str:
    # A Business Manager system-user token has no Page; the Instagram account
    # is assigned to it directly instead.
    ig_id = get_optional_env_var("IG_USER_ID")
    if ig_id:
        return ig_id
    accounts = _call(
        "GET", "me/assigned_instagram_accounts", token, params={"fields": "id"}
    )["data"]
    if not accounts:
        raise RuntimeError("No Instagram account is assigned to this token")
    return accounts[0]["id"]


def post_images_on_instagram(hadith: Hadith, images) -> str:
    token = get_token()
    ig_id = get_ig_user_id(token)

    with temp_public_urls([to_jpeg(img) for img in images]) as urls:
        caption = make_caption(hadith)
        if len(urls) == 1:
            creation_id = _call(
                "POST",
                f"{ig_id}/media",
                token,
                data={"image_url": urls[0], "caption": caption},
            )["id"]
        else:
            children = [
                _call(
                    "POST",
                    f"{ig_id}/media",
                    token,
                    data={"image_url": u, "is_carousel_item": "true"},
                )["id"]
                for u in urls
            ]
            for child in children:
                _wait_until_ready(child, token)
            creation_id = _call(
                "POST",
                f"{ig_id}/media",
                token,
                data={
                    "media_type": "CAROUSEL",
                    "children": ",".join(children),
                    "caption": caption,
                },
            )["id"]

        _wait_until_ready(creation_id, token)
        # Instagram copies the images on publish, so the branch can go after
        media_id = _call(
            "POST",
            f"{ig_id}/media_publish",
            token,
            data={"creation_id": creation_id},
        )["id"]
    print(f"Posted on Instagram: {media_id}")
    return media_id


def post_on_instagram(hadith: Hadith) -> bool:
    """Return False when the hadith is too long for cards and was skipped."""
    images = render_hadith_images(hadith)
    if images is None:
        print("Hadith too long for image cards, skipping")
        return False
    post_images_on_instagram(hadith, images)
    return True
