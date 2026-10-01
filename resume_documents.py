"""PDF validation, extraction and a readable, single-column resume layout."""
import io
import re
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader

MAX_PDF_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 20
MAX_RESUME_TEXT = 24000


class InvalidPDF(ValueError):
    pass


def inspect_pdf(content):
    if not content or len(content) > MAX_PDF_BYTES:
        raise InvalidPDF("Envie um PDF não vazio de até 8 MB.")
    if not content.startswith(b"%PDF-"):
        raise InvalidPDF("O conteúdo do arquivo não é um PDF válido. Exporte seu currículo como PDF e tente novamente.")
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise InvalidPDF("O PDF está protegido por senha. Envie uma cópia sem senha.")
        page_count = len(reader.pages)
        if not 1 <= page_count <= MAX_PDF_PAGES:
            raise InvalidPDF(f"O currículo deve ter entre 1 e {MAX_PDF_PAGES} páginas.")
        texts = []
        for page in reader.pages:
            # Force parsing of each page before accepting it for storage.
            text = page.extract_text() or ""
            texts.append(text)
            if sum(map(len, texts)) > MAX_RESUME_TEXT:
                raise InvalidPDF("O PDF tem texto demais para um currículo. Envie uma versão mais objetiva.")
        text = "\n".join(texts).strip()
    except InvalidPDF:
        raise
    except Exception as exc:
        raise InvalidPDF("Não foi possível abrir este PDF. O arquivo pode estar incompleto ou corrompido.") from exc
    return {"text": text, "pages": page_count, "words": len(text.split()), "readable": len(text.strip()) >= 60}


def text_from_resume(data):
    return "\n".join([data.get("name", ""), data.get("headline", ""), *data.get("contacts", []), *[f"{s['title']}\n{s['content']}" for s in data.get("sections", [])]])


def safe_text(value):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))
    return escape(text).replace("\n", "<br/>")


def build_resume_pdf(data):
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    fonts = Path(reportlab.__file__).parent / "fonts"
    if "ResumeSans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ResumeSans", str(fonts / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("ResumeSansBold", str(fonts / "VeraBd.ttf")))
        pdfmetrics.registerFontFamily("ResumeSans", normal="ResumeSans", bold="ResumeSansBold", italic="ResumeSans", boldItalic="ResumeSansBold")
    ink, accent, muted = colors.HexColor("#172B3A"), colors.HexColor("#216E79"), colors.HexColor("#53636E")
    base = dict(fontName="ResumeSans", textColor=ink, alignment=TA_LEFT, splitLongWords=True)
    styles = {
        "name": ParagraphStyle("Name", **base, fontSize=23, leading=29, spaceAfter=8),
        "headline": ParagraphStyle("Headline", **{**base, "textColor": accent}, fontSize=11, leading=16, spaceAfter=7),
        "contact": ParagraphStyle("Contact", **{**base, "textColor": muted}, fontSize=9, leading=14, spaceAfter=4),
        "heading": ParagraphStyle("Section", **{**base, "fontName": "ResumeSansBold", "textColor": accent}, fontSize=9.5, leading=14, spaceBefore=16, spaceAfter=6, keepWithNext=True),
        "body": ParagraphStyle("Body", **base, fontSize=10, leading=15, spaceAfter=5),
        "bullet": ParagraphStyle("Bullet", **base, fontSize=10, leading=15, spaceAfter=4, leftIndent=10, firstLineIndent=-8),
    }
    stream = io.BytesIO()
    document = SimpleDocTemplate(stream, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                                 topMargin=1.65 * cm, bottomMargin=1.7 * cm, title=f"Currículo - {data['name']}", author=data["name"])
    story = [Paragraph(safe_text(data["name"]), styles["name"])]
    if data.get("headline"):
        story.append(Paragraph(safe_text(data["headline"]), styles["headline"]))
    if data.get("contacts"):
        story.append(Paragraph(" &nbsp; | &nbsp; ".join(safe_text(v) for v in data["contacts"]), styles["contact"]))
    story.extend([Spacer(1, 10), HRFlowable(width="100%", thickness=1.3, color=accent), Spacer(1, 2)])
    for section in data["sections"]:
        story.append(Paragraph(safe_text(section["title"].upper()), styles["heading"]))
        for line in section["content"].splitlines():
            line = line.strip()
            if not line:
                continue
            bullet = bool(re.match(r"^[-•*]\s+", line))
            text = re.sub(r"^[-•*]\s+", "", line) if bullet else line
            story.append(Paragraph(("• " if bullet else "") + safe_text(text), styles["bullet" if bullet else "body"]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#DDE4E8"))
        canvas.line(doc.leftMargin, 1.3 * cm, A4[0] - doc.rightMargin, 1.3 * cm)
        canvas.setFont("ResumeSans", 8)
        canvas.setFillColor(muted)
        canvas.drawString(doc.leftMargin, .85 * cm, str(data["name"])[:65])
        canvas.drawRightString(A4[0] - doc.rightMargin, .85 * cm, str(doc.page))
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    stream.seek(0)
    return stream
