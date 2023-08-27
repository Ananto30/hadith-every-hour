from tweepy.errors import TweepyException

from src.facebook_page import post_on_facebook_page
from src.hadith_src import query_hadith
from src.tracker import get_hadith_track, update_hadith_track
from src.twitter import tweet


def tweet_hadith():
    collection, book, hadith_no = get_hadith_track()

    if hadith := query_hadith(collection, book, hadith_no):
        # try:
        #     tweet(hadith)
        # except TweepyException as e:
        #     print(e)

        post_on_facebook_page(hadith)

        update_hadith_track(collection, book, hadith_no)


if __name__ == "__main__":
    tweet_hadith()
