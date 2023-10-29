from dataclasses import asdict, dataclass
from typing import Dict, Optional


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
    highlights: Optional[Dict] = None
    hadith_link: Optional[str] = None
    base64: Optional[str] = None
    score: Optional[float] = None

    def dict(self):
        return asdict(self)
