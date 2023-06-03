from typing import Optional
import requests

from src.model import Hadith

hadith_source = "https://ask-hadith.vercel.app/api/book"


def query_hadith(collection: str, book: int, hadith_no: int) -> Optional[Hadith]:
    full_hadith_source = "https://askhadith.com/book"
    hadith_link = f"{full_hadith_source}?collection_id={collection}&book={book}&ref_no={hadith_no}"

    print(f"Querying {hadith_link}")

    resp = requests.get(
        f"{hadith_source}?collection_id={collection}&book={book}&ref_no={hadith_no}"
    )

    if resp.json():
        data = resp.json()
        # data.pop("_id")
        hadith = Hadith(**data)
        hadith.hadith_link = hadith_link

        print(f"Found hadith: {hadith}")

        return hadith
    
    print(f"Could not find hadith: {resp.content}")
