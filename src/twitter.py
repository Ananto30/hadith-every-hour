import os
from typing import List

import tweepy

from src.model import Hadith
from src.utils import ensure_env_var

tweet_char_limit = 260
total_tweet_thread_char_limit = 4 * 260  # should review again


def make_tweet(hadith: Hadith):
    """
    Make only one Tweet body.
    """
    full_hadith = "\n".join([hadith.narrator_en, hadith.body_en, hadith.hadith_no])
    if len(full_hadith) > tweet_char_limit:
        link = f"\nFull hadith: {hadith.hadith_link}"
        full_hadith = full_hadith[: (tweet_char_limit - (len(link) + 3))] + "..." + link

    return full_hadith


def get_prev_word_end_index(i, full_hadith) -> int:
    while full_hadith[i] != " ":
        i -= 1
    return i


def make_tweet_thread(hadith: Hadith) -> List[str]:
    """
    Make several Tweet bodies.
    First body can be the main Tweet and the followings are comments
    that can be seen as a thread in Twitter.
    """
    hadith.body_en = hadith.body_en.replace("ﷺ", "PBUH")
    full_hadith = "\n".join(
        [
            f"{hadith.collection} (Book {hadith.book_no}, Hadith {hadith.book_ref_no})",
            hadith.narrator_en if hadith.narrator_en else "",
            hadith.body_en,
        ]
    )
    i, j = 0, 0
    chunks = []
    while i < len(full_hadith) and i < total_tweet_thread_char_limit:
        j += tweet_char_limit
        if j < len(full_hadith) and full_hadith[j] != " ":
            j = get_prev_word_end_index(j, full_hadith)
        chunks.append(full_hadith[i:j])
        i = j

    link = (
        f"\n.........This is a long Hadith, please continue reading here: {hadith.hadith_link}"
        if i > total_tweet_thread_char_limit
        else f"\nFor convenient reading: {hadith.hadith_link}"
    )
    if len(chunks[-1]) < (tweet_char_limit - len(link)):
        chunks[-1] = chunks[-1] + link
    else:
        chunks.append(link)

    return chunks


def tweet(hadith: Hadith):
    auth = tweepy.OAuthHandler(
        ensure_env_var("API_KEY"),
        ensure_env_var("API_SECRET"),
    )
    auth.set_access_token(
        ensure_env_var("ACCESS_TOKEN"),
        ensure_env_var("ACCESS_TOKEN_SECRET"),
    )
    api = tweepy.API(auth)

    chunks = make_tweet_thread(hadith)
    status = api.update_status(chunks[0])
    for i in range(1, len(chunks)):
        status = api.update_status(
            f"@HadithEveryHour {chunks[i]}", in_reply_to_status_id=status.id
        )

    print(f"Tweeted: {status.text}")
