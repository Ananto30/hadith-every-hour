import time
from typing import List

import tweepy

from src.config import Twitter
from src.model import Hadith
from src.utils import ensure_env_var


def make_tweet(hadith: Hadith):
    """
    Make only one Tweet body.
    """
    full_hadith = "\n".join(
        [hadith.narrator_en, hadith.body_en, hadith.hadith_no]
    )
    if len(full_hadith) > Twitter.char_limit:
        link = f"\nFull hadith: {hadith.hadith_link}"
        full_hadith = (
            full_hadith[: (Twitter.char_limit - (len(link) + 3))]
            + "..."
            + link
        )

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
    while i < len(full_hadith) and i < Twitter.total_thread_char_limit:
        j += Twitter.char_limit
        if j < len(full_hadith) and full_hadith[j] != " ":
            j = get_prev_word_end_index(j, full_hadith)
        chunks.append(full_hadith[i:j])
        i = j

    link = (
        f"\n.........This is a long Hadith, please continue reading here: {hadith.hadith_link}"
        if i > Twitter.total_thread_char_limit
        else f"\nFor convenient reading: {hadith.hadith_link}"
    )
    if len(chunks[-1]) < (Twitter.char_limit - len(link)):
        chunks[-1] = chunks[-1] + link
    else:
        chunks.append(link)

    return chunks


def tweet(hadith: Hadith):
    client = tweepy.Client(
        consumer_key=ensure_env_var(Twitter.consumer_key),
        consumer_secret=ensure_env_var(Twitter.consumer_secret),
        access_token=ensure_env_var(Twitter.access_token),
        access_token_secret=ensure_env_var(Twitter.access_token_secret),
    )

    chunks = make_tweet_thread(hadith)
    resp = client.create_tweet(text=chunks[0])
    status_id = resp.data.get("id")

    comments = []
    for i in range(1, len(chunks)):
        res = client.create_tweet(
            text=f"@HadithEveryHour {chunks[i]}",
            in_reply_to_tweet_id=status_id,
        )
        comments.append(res.data)
        time.sleep(1)

    print(f"Tweeted: status={resp}\n\n comments={comments}")
