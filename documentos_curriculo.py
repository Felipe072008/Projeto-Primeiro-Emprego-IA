"""Valida PDFs enviados e monta o documento do currículo com layout consistente."""
import io
import re
from pathlib import Path
from modelo_curriculo import presentation
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
    model = presentation(data)
    parts = [model['name'], model['contact'], model['link'], model['headline']]
    for section in model['sections']:
        parts.append(section['title'])
        for item in section['records']:
            parts.extend(row['bold'] + row['text'] + row['detail'] for row in item)
    return "\n".join(filter(None, parts))


def safe_text(value):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))
    return escape(text).replace("\n", "<br/>")


def build_resume_pdf(data):
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, KeepTogether

    fonts = Path(reportlab.__file__).parent / 'fonts'
    if 'ResumeSans' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('ResumeSans', str(fonts / 'Vera.ttf')))
        pdfmetrics.registerFont(TTFont('ResumeSansBold', str(fonts / 'VeraBd.ttf')))
        pdfmetrics.registerFontFamily('ResumeSans', normal='ResumeSans', bold='ResumeSansBold', italic='ResumeSans', boldItalic='ResumeSansBold')
    model = presentation(data)
    def style(name, size, leading, color, *, bold=False, **options):
        return ParagraphStyle(name, fontName='ResumeSansBold' if bold else 'ResumeSans',
                              fontSize=size, leading=leading, textColor=colors.HexColor(color), **options)

    accent = model['color']
    name = style('Name', 24, 29, accent, bold=True, alignment=1)
    contact = style('Contacts', 10, 14, '#475569', alignment=1, spaceBefore=3)
    heading = style('Heading', 12.5, 16, accent, bold=True, spaceBefore=18, spaceAfter=3)
    body = style('Body', 10, 14, '#1E293B')
    bullet = style('Bullet', 10, 14, '#1E293B', leftIndent=13, bulletIndent=1)
    stream = io.BytesIO()
    document = SimpleDocTemplate(stream, pagesize=A4, leftMargin=1.8*cm-6, rightMargin=1.8*cm-6,
                                 topMargin=1.8*cm-6, bottomMargin=1.8*cm-6, title=data['name'])
    story = [Paragraph(safe_text(model['name']), name)]
    for value in (model['contact'], model['link'], model['headline']):
        if value:
            story.append(Paragraph(safe_text(value), contact))
    story.extend([Spacer(1, 12), HRFlowable(width='100%', thickness=1.5, color=colors.HexColor(accent))])
    for section in model['sections']:
        intro = [Paragraph(safe_text(section['title']), heading),
                 HRFlowable(width='100%', thickness=.75, color=colors.HexColor('#CBD5E1'), spaceAfter=5)]
        for item in section['records']:
            paragraphs = []
            for row in item:
                text = ('<b>' + safe_text(row['bold']) + '</b>' + safe_text(row['text'])
                        + '<font color="#475569">' + safe_text(row['detail']) + '</font>')
                paragraphs.append(Paragraph(text, bullet if row['bullet'] else body,
                                            bulletText='•' if row['bullet'] else None))
            story.append(KeepTogether(intro + paragraphs))
            intro = []
            story.append(Spacer(1, 3))
    document.build(story)
    stream.seek(0)
    return stream
