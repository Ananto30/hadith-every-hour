"""Render a hadith as a set of calm, readable 4:5 image cards (1080x1350)."""

import io
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.model import Hadith

FONT_DIR = Path(__file__).resolve().parent.parent / "resources" / "fonts"

W, H = 1080, 1350
MARGIN = 120
BODY_TOP, BODY_BOTTOM = 270, 1110
LINE_SPACING = 1.55

# Largest size first. The smallest one decides if the hadith is too long.
BODY_SIZES = (64, 58, 52, 48, 44)
NARRATOR_SIZES = (36, 32, 28, 24)
MAX_PAGES = 3
# Keeps every card airy even when the font is small
MAX_LINES = 10

TOP_COLOR = (248, 245, 237)
BOTTOM_COLOR = (228, 236, 226)
INK = (43, 42, 38)
MUTED = (122, 124, 114)
ACCENT = (110, 140, 118)
RULE = (205, 215, 200)

# Literata has no Arabic glyphs (e.g. the ﷺ ligature), so those use Amiri.
ARABIC = re.compile(
    r"([\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+)"
)
SENTENCE_END = (".", "?", "!", ".”", "?”", "!”")


@lru_cache(maxsize=None)
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT_DIR / name), size)
    if name.startswith("Literata"):
        # Axes are [optical size, weight]; high optical size suits big text
        font.set_variation_by_axes([min(72, max(7, size)), 400])
    return font


def _serif(size: int):
    return _font("Literata.ttf", size)


def _italic(size: int):
    return _font("Literata-Italic.ttf", size)


def _arabic(size: int):
    return _font("Amiri-Regular.ttf", size)


def clean_text(text: str) -> str:
    """The source data uses ASCII quotes and backticks for the 'ayn."""
    # ‘ instead of ʿ (U+02BF): same look, but ʿ has a wide gap in Literata
    text = text.replace("`", "‘")
    text = re.sub(r"(^|\s)'(?=\w)", r"\1‘", text).replace("'", "’")
    text = re.sub(r'(^|[\s(\[])"(?=\S)', r"\1“", text)
    return " ".join(text.replace('"', "”").split())


def _pieces(word: str, size: int):
    for part in ARABIC.split(word):
        if part:
            yield part, (
                _arabic(size) if ARABIC.fullmatch(part) else _serif(size)
            )


def _word_width(word: str, size: int) -> float:
    return sum(f.getlength(p) for p, f in _pieces(word, size))


def _wrap(text: str, size: int, max_width: int) -> list[str]:
    space = _serif(size).getlength(" ")
    lines: list[str] = []
    line: list[str] = []
    width = 0.0
    for word in text.split():
        w = _word_width(word, size)
        if line and width + space + w > max_width:
            lines.append(" ".join(line))
            line, width = [], 0.0
        width += w + (space if line else 0)
        line.append(word)
    if line:
        lines.append(" ".join(line))
    return lines


def _capacity(size: int) -> int:
    fits = int((BODY_BOTTOM - BODY_TOP) // (size * LINE_SPACING))
    return min(fits, MAX_LINES)


def _paginate(lines: list[str], pages: int, cap: int) -> list[list[str]]:
    """Split into balanced pages, nudging cuts to sentence ends when close."""
    cuts = [0]
    for k in range(1, pages):
        ideal = round(k * len(lines) / pages)
        window = [
            i
            for i in range(ideal - 2, ideal + 3)
            if cuts[-1] < i < len(lines)
            and lines[i - 1].endswith(SENTENCE_END)
        ]
        cuts.append(
            min(window, key=lambda i: abs(i - ideal)) if window else ideal
        )
    cuts.append(len(lines))
    chunks = [lines[a:b] for a, b in zip(cuts, cuts[1:])]
    if any(len(c) > cap for c in chunks):
        # Sentence nudging overfilled a page, so fall back to even cuts
        step = math.ceil(len(lines) / pages)
        chunks = [lines[i : i + step] for i in range(0, len(lines), step)]
    return chunks


def _layout(text: str):
    """Pick the biggest font that doesn't add pages; None if too long."""
    max_width = W - 2 * MARGIN
    needed = None
    for size in reversed(BODY_SIZES):
        lines = _wrap(text, size, max_width)
        pages = math.ceil(len(lines) / _capacity(size))
        if needed is None:
            if pages > MAX_PAGES:
                return None
            needed = pages
        if pages == needed:
            best = (size, lines, pages)
    size, lines, pages = best
    return size, _paginate(lines, pages, _capacity(size))


def _background() -> Image.Image:
    mask = Image.linear_gradient("L").resize((W, H))
    img = Image.composite(
        Image.new("RGB", (W, H), BOTTOM_COLOR),
        Image.new("RGB", (W, H), TOP_COLOR),
        mask,
    )
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        (44, 44, W - 44, H - 44), radius=28, outline=RULE, width=2
    )
    return img


def _ornament(d: ImageDraw.ImageDraw, y: int):
    cx, r = W // 2, 9
    d.line((cx - 150, y, cx - 24, y), fill=RULE, width=2)
    d.line((cx + 24, y, cx + 150, y), fill=RULE, width=2)
    d.polygon(
        [(cx, y - r), (cx + r, y), (cx, y + r), (cx - r, y)], fill=ACCENT
    )


def _draw_line(d, line: str, size: int, y: int):
    space = _serif(size).getlength(" ")
    words = line.split()
    total = sum(_word_width(w, size) for w in words) + space * (len(words) - 1)
    x = (W - total) / 2
    for i, word in enumerate(words):
        for part, font in _pieces(word, size):
            d.text((x, y), part, font=font, fill=INK, anchor="ls")
            x += font.getlength(part)
        x += space


def _center(d, y: int, text: str, font, fill):
    d.text((W / 2, y), text, font=font, fill=fill, anchor="ms")


def _narrator_lines(text: str):
    """Biggest italic size that fits in 2 lines; long names shrink, never clip."""
    max_width = W - 2 * MARGIN
    for size in NARRATOR_SIZES:
        font = _italic(size)
        lines: list[str] = [""]
        for word in text.split():
            trial = f"{lines[-1]} {word}".strip()
            if lines[-1] and font.getlength(trial) > max_width:
                lines.append(word)
            else:
                lines[-1] = trial
        if len(lines) <= 2:
            break
    return font, size, lines


def _render_page(hadith: Hadith, lines, size, index, total) -> Image.Image:
    img = _background()
    d = ImageDraw.Draw(img)
    _ornament(d, 130)

    if index == 0 and hadith.narrator_en:
        font, nsize, nlines = _narrator_lines(clean_text(hadith.narrator_en))
        # Start higher when wrapped so the 2nd line stays clear of the body
        y = 205 if len(nlines) == 1 else 195
        for i, nline in enumerate(nlines):
            _center(d, round(y + i * nsize * 1.3), nline, font, MUTED)

    lines = list(lines)
    if index > 0:
        lines[0] = "… " + lines[0]
    if index < total - 1:
        lines[-1] += " …"

    line_h = size * LINE_SPACING
    top = BODY_TOP + (BODY_BOTTOM - BODY_TOP - line_h * len(lines)) / 2
    for i, line in enumerate(lines):
        # +size*0.8 puts the baseline roughly where the line box expects it
        _draw_line(d, line, size, round(top + i * line_h + size * 0.8))

    _ornament(d, 1170)
    _center(
        d, 1230, f"{hadith.collection} · {hadith.hadith_no}", _serif(32), INK
    )
    footer = "askhadith.com" + (
        f"  ·  {index + 1} / {total}" if total > 1 else ""
    )
    _center(d, 1275, footer, _serif(26), MUTED)
    return img


def render_hadith_images(hadith: Hadith) -> list[Image.Image] | None:
    """Return one image per page, or None if the hadith is too long."""
    layout = _layout(clean_text(hadith.body_en))
    if layout is None:
        return None
    size, pages = layout
    return [
        _render_page(hadith, p, size, i, len(pages))
        for i, p in enumerate(pages)
    ]


def to_jpeg(img: Image.Image) -> bytes:
    """JPEG, since Instagram's publishing API only accepts JPEG."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92, optimize=True)
    return buf.getvalue()


def save_images(
    images: list[Image.Image], out_dir: str, stem: str
) -> list[str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    for i, img in enumerate(images, 1):
        path = f"{out_dir}/{stem}_{i}.jpg"
        Path(path).write_bytes(to_jpeg(img))
        paths.append(path)
    return paths


if __name__ == "__main__":
    from src.hadith_src import query_hadith

    collection, book, number = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    found = query_hadith(collection, book, number)
    imgs = render_hadith_images(found) if found else None
    if not imgs:
        sys.exit("Hadith not found or too long")
    print("\n".join(save_images(imgs, "out", f"{collection}_{book}_{number}")))
