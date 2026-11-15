import sys
from functools import partial

from src.config import Facebook
from src.facebook_page import post_on_facebook_page
from src.hadith_src import query_hadith
from src.tracker import get_hadith_track, update_hadith_track


def get_hadith(tracker_file):
    collection, book, hadith_no = get_hadith_track(tracker_file)
    return query_hadith(collection, book, hadith_no)


get_hadith_for_facebook = partial(get_hadith, Facebook.tracker_file)

update_tracker_for_facebook = partial(
    update_hadith_track, Facebook.tracker_file
)


def post(platform):
    if platform == "fb":
        hadith = get_hadith_for_facebook()
        if not hadith:
            raise ValueError("No hadith found")
        post_on_facebook_page(hadith)
        update_tracker_for_facebook()


if __name__ == "__main__":
    arg = sys.argv[1]
    if not arg:
        raise ValueError("Please provide where to post: fb")
    post(arg)
