import requests

from facebook_page import post_on_page
from model import Hadith
from tracker import get_hadith_track, update_hadith_track
from twitter import tweet
from tweepy.errors import TweepyException


def tweet_hadith():
    collection, book, hadith_no = get_hadith_track()

    hadith_source = "https://ask-hadith.vercel.app/api/book"
    full_hadith_source = "https://askhadith.com/book"
    hadith_link = f"{full_hadith_source}?collection_id={collection}&book={book}&ref_no={hadith_no}"

    resp = requests.get(f"{hadith_source}?collection_id={collection}&book={book}&ref_no={hadith_no}")
    if resp.json():
        data = resp.json()
        data.pop('_id')
        hadith = Hadith(**data)
        hadith.hadith_link = hadith_link
        try:
            tweet(hadith)
        except TweepyException as e:
            print(e)
        post_on_page(hadith)
        update_hadith_track(collection, book, hadith_no)


if __name__ == "__main__":
    tweet_hadith()
