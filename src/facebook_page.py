import urllib.parse

import requests

from src.fb_token import load_state
from src.model import Hadith
from src.utils import ensure_env_var, get_optional_env_var


def format_post(hadith: Hadith) -> str:
    link = (
        urllib.parse.quote_plus(hadith.hadith_link)
        if hadith.hadith_link
        else ""
    )
    reference = (
        f"{hadith.collection} (Book {hadith.book_no}, "
        f"Hadith {hadith.book_ref_no} [Reference {hadith.hadith_no}])"
    )
    return "\n".join(
        [
            f"{hadith.narrator_en}",
            hadith.body_en,
            f"\n{reference}",
            f"Book: {hadith.book_en}",
            f"Chapter: ({hadith.chapter_no}) {hadith.chapter_en}"
            if hadith.chapter_en
            else "",
            f"\n\nLink: {link}",
        ]
    )


def get_page_token() -> str:
    """Prefer the rotated token from the encrypted state file.

    FB_PAGE_TOKEN is only a bootstrap fallback for the first deployment. It
    can be deleted after the refresh workflow has committed the state file.
    """
    state = load_state()
    if state is not None:
        return state.page_token

    token = get_optional_env_var("FB_PAGE_TOKEN")
    if not token:
        raise ValueError(
            "No Facebook Page token available. Run the Refresh Facebook "
            "token workflow, or set the FB_PAGE_TOKEN secret."
        )
    return token


def post_on_facebook_page(hadith: Hadith):
    access_token = get_page_token()
    page_id = ensure_env_var("FB_PAGE_ID")
    msg = format_post(hadith)

    resp = requests.post(
        f"https://graph.facebook.com/{page_id}/feed",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"message": msg},
        timeout=10,
    )
    resp.raise_for_status()
    print(f"Posted on FB {resp.content.decode('utf-8')}")
