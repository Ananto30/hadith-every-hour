import os

import requests
import urllib.parse

from src.model import Hadith


def format_post(hadith: Hadith) -> str:
    link = urllib.parse.quote_plus(hadith.hadith_link)
    return "\n".join(
        [
            f"{hadith.collection} (Book {hadith.book_no}, Hadith {hadith.book_ref_no} [Reference {hadith.hadith_no}])",
            f"Book: {hadith.book_en}",
            f"Chapter: ({hadith.chapter_no}) {hadith.chapter_en}"
            if hadith.chapter_en
            else "",
            f"\n{hadith.narrator_en}",
            hadith.body_en,
            f"\n\nLink: {link}",
        ]
    )


def post_on_facebook_page(hadith: Hadith):
    access_token = os.getenv("FB_PAGE_TOKEN")
    page_id = os.getenv("FB_PAGE_ID")
    msg = format_post(hadith)

    resp = requests.post(
        f"https://graph.facebook.com/{page_id}/feed?message={msg}&access_token={access_token}"
    )

    print(f"Posted on FB {resp.content}")
