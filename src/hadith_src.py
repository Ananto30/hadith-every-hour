from pprint import pprint

import requests

from src.model import Hadith

hadith_source = "https://ask-hadith.vercel.app/api/book"


def query_hadith(
    collection: str,
    book: int,
    hadith_no: int,
) -> Hadith | None:
    # Clean canonical URL; the old /book?... links only 301 to this
    hadith_link = f"https://www.askhadith.com/hadith/{collection}/{book}/{hadith_no}"

    print(f"Querying {hadith_link}")

    resp = requests.get(
        f"{hadith_source}?collection_id={collection}&book={book}&ref_no={hadith_no}",
        timeout=10,
    )

    if resp.json():
        data = resp.json()
        hadith = Hadith(**data)
        hadith.hadith_link = hadith_link

        print("================= Found hadith =================")
        pprint(hadith.dict())
        print("================================================")

        return hadith

    print(f"Could not find hadith: {resp.content.decode('utf-8')}")

    return None
