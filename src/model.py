from dataclasses import asdict, dataclass


@dataclass
class Hadith:
    body_en: str
    book_en: str
    book_no: str
    book_ref_no: str
    chapter_en: str
    chapter_no: str
    collection: str
    collection_id: str
    hadith_grade: str
    hadith_no: str
    narrator_en: str
    highlights: dict | None = None
    hadith_link: str | None = None
    base64: str | None = None
    score: float | None = None

    def dict(self):
        return asdict(self)
