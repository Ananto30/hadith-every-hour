import sys
import warnings
from functools import partial

from src.config import Facebook, Twitter
from src.facebook_page import post_on_facebook_page
from src.hadith_src import query_hadith
from src.tracker import get_hadith_track, update_hadith_track
from src.twitter import tweet


def get_hadith(tracker_file):
    collection, book, hadith_no = get_hadith_track(tracker_file)
    return query_hadith(collection, book, hadith_no)


get_hadith_for_twitter = partial(get_hadith, Twitter.tracker_file)
get_hadith_for_facebook = partial(get_hadith, Facebook.tracker_file)

update_tracker_for_twitter = partial(update_hadith_track, Twitter.tracker_file)
update_tracker_for_facebook = partial(
    update_hadith_track, Facebook.tracker_file
)


def tweet_or_post(platform):
    if platform == "tweet":
        hadith = get_hadith_for_twitter()
        if not hadith:
            raise ValueError("No hadith found")
        tweet(hadith)
        update_tracker_for_twitter()

    if platform == "fb":
        hadith = get_hadith_for_facebook()
        if not hadith:
            raise ValueError("No hadith found")
        post_on_facebook_page(hadith)
        update_tracker_for_facebook()


if __name__ == "__main__":
    arg = sys.argv[1]
    if not arg:
        raise ValueError("Please provide where to post: tweet or fb")
    tweet_or_post(arg)
