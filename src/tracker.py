import json
from typing import Tuple


def get_hadith_track() -> Tuple[str, int, int]:
    with open("resources/hadith_track.json", "r") as json_file:
        data = json.load(json_file)
        return (
            data.get("collection"),
            int(data.get("book")),
            int(data.get("hadith")),
        )


def update_hadith_track(collection, book, hadith):
    # TODO: need to make dynamic
    with open("resources/bukhari_books.json", "r") as json_file:
        data = json.load(json_file)

    if data.get(str(book)) > hadith:
        hadith += 1
    else:
        hadith = 1
        book += 1

    with open("resources/hadith_track.json", "w") as json_file:
        json.dump(
            {
                "collection": collection,
                "book": book,
                "hadith": hadith,
            },
            json_file,
            indent=2,
        )
