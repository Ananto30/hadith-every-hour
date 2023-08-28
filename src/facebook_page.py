import urllib.parse

import requests

from src.model import Hadith
from utils import decrypt, encrypt, ensure_env_var


def format_post(hadith: Hadith) -> str:
    link = urllib.parse.quote_plus(hadith.hadith_link) if hadith.hadith_link else ""
    return "\n".join(
        [
            f"{hadith.narrator_en}",
            hadith.body_en,
            f"\n{hadith.collection} (Book {hadith.book_no}, Hadith {hadith.book_ref_no} [Reference {hadith.hadith_no}])",
            f"Book: {hadith.book_en}",
            f"Chapter: ({hadith.chapter_no}) {hadith.chapter_en}"
            if hadith.chapter_en
            else "",
            f"\n\nLink: {link}",
        ]
    )


def post_on_facebook_page(hadith: Hadith):
    access_token = get_fb_token_from_file()
    page_id = ensure_env_var("FB_PAGE_ID")
    msg = format_post(hadith)

    resp = requests.post(
        f"https://graph.facebook.com/{page_id}/feed?message={msg}&access_token={access_token}",
        timeout=10,
    )
    print(f"Posted on FB {resp.content.decode('utf-8')}")

    renew_fb_page_token(access_token)


def renew_fb_page_token(old_token):
    app_id = ensure_env_var("FB_APP_ID")
    app_secret = ensure_env_var("FB_APP_SECRET")

    resp = requests.get(
        f"https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={old_token}",
        timeout=10,
    )
    new_token = resp.json()["access_token"]
    update_token_file(new_token)

    print("Renewed FB page token")


def get_fb_token_from_file() -> str:
    with open("resources/fb_token.txt", "r") as token_file:
        return decrypt_with_secret_key(token_file.read().strip())


def update_token_file(new_token) -> None:
    with open("resources/fb_token.txt", "w") as token_file:
        token_file.write(encrypt_with_secret_key(new_token))


def encrypt_with_secret_key(value: str) -> str:
    key = ensure_env_var("TOKEN_ENCRYPTION_KEY")
    return encrypt(key, value)


def decrypt_with_secret_key(value: str) -> str:
    key = ensure_env_var("TOKEN_ENCRYPTION_KEY")
    return decrypt(key, value)
