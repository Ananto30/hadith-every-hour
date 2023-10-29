import json
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Tracker:
    collection: str
    book: int
    hadith: int

    @classmethod
    def from_file(cls, tracker_file):
        with open(tracker_file, "r") as json_file:
            data = json.load(json_file)
            return cls(
                collection=data.get("collection"),
                book=int(data.get("book")),
                hadith=int(data.get("hadith")),
            )

    def to_file(self, tracker_file):
        with open(tracker_file, "w") as json_file:
            json.dump(
                {
                    "collection": self.collection,
                    "book": self.book,
                    "hadith": self.hadith,
                },
                json_file,
                indent=2,
            )


def get_hadith_track(tracker_file) -> Tuple[str, int, int]:
    tracker = Tracker.from_file(tracker_file)
    return tracker.collection, tracker.book, tracker.hadith


def update_hadith_track(tracker_file):
    collection, book, hadith = get_hadith_track(tracker_file)

    with open("resources/bukhari_books.json", "r") as json_file:
        data = json.load(json_file)

    print(f"Updating tracker: {data}")
    print(f"Updating tracker: {collection}, {book}, {hadith}")
    if data.get(str(book)) > hadith:
        hadith += 1
    else:
        hadith = 1
        book += 1

    tracker = Tracker(collection, book, hadith)
    tracker.to_file(tracker_file)
