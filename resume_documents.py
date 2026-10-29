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


def resume_section_paragraphs(section):
    """Format saved text without interpreting user content as markup."""
    records = section['title'] in {'Formação acadêmica', 'Curso em andamento ou concluído',
                                   'Experiência profissional', 'Experiências acadêmicas e projetos',
                                   'Cursos e certificações'}
    skills = section['title'] == 'Habilidades'
    groups = re.split(r'\n\s*\n', section['content'].strip())
    for group in groups:
        lines = [line.strip() for line in re.split(r'[;\n]+' if skills else r'\n', group) if line.strip()]
        for index, line in enumerate(lines):
            bullet = skills or bool(re.match(r'^[-•●*]\s+', line))
            line = re.sub(r'^[-•●*]\s+', '', line) if bullet else line
            text = safe_text(line)
            if records and index == 0 and not bullet and len(line.partition(' · ')[0]) <= 180:
                title, separator, details = line.partition(' · ')
                text = '<b>' + safe_text(title) + '</b>' + (safe_text(separator + details) if separator else '')
            yield text, bullet, records and index == 0 and len(lines) > 1 and len(line.partition(' · ')[0]) <= 180, index == len(lines) - 1


def resume_contact_text(contact):
    if re.fullmatch(r'(?:\d{10,11}|\(\d{2}\) ?\d{4,5}-\d{4})', contact):
        return 'Telefone', re.sub(r'^(\d{2})(\d{4,5})(\d{4})$', r'(\1) \2-\3', contact)
    return ('E-mail' if '@' in contact else 'Localização'), contact


def build_resume_pdf(data):
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    fonts = Path(reportlab.__file__).parent / 'fonts'
    if 'ResumeSans' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('ResumeSans', str(fonts / 'Vera.ttf')))
        pdfmetrics.registerFont(TTFont('ResumeSansBold', str(fonts / 'VeraBd.ttf')))
        pdfmetrics.registerFontFamily('ResumeSans', normal='ResumeSans', bold='ResumeSansBold', italic='ResumeSans', boldItalic='ResumeSansBold')
    base = dict(fontName='ResumeSans', textColor=colors.black, splitLongWords=True)
    styles = {
        'name': ParagraphStyle('Name', **{**base, 'fontName': 'ResumeSansBold'}, fontSize=22, leading=27, spaceAfter=9),
        'headline': ParagraphStyle('Headline', **base, fontSize=10.5, leading=15, spaceAfter=4),
        'contact': ParagraphStyle('Contact', **base, fontSize=9.5, leading=14, spaceAfter=3),
        'heading': ParagraphStyle('Section', **{**base, 'fontName': 'ResumeSansBold'}, fontSize=12, leading=16),
        'body': ParagraphStyle('Body', **base, fontSize=10.5, leading=14, spaceAfter=3),
        'bullet': ParagraphStyle('Bullet', **base, fontSize=10.5, leading=14, spaceAfter=3, leftIndent=13, bulletIndent=1),
    }
    stream = io.BytesIO()
    document = SimpleDocTemplate(stream, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                                 topMargin=1.7 * cm, bottomMargin=1.6 * cm, title=f"Currículo - {data['name']}", author=data['name'])
    story = [Paragraph(safe_text(data['name'].upper()), styles['name'])]
    if data.get('headline'):
        story.append(Paragraph(safe_text(data['headline']), styles['headline']))
    story.extend([Spacer(1, 10), HRFlowable(width='100%', thickness=.8, color=colors.black), Spacer(1, 12)])
    for contact in data.get('contacts', []):
        label, value = resume_contact_text(contact)
        story.append(Paragraph('<b>' + label + ':</b> ' + safe_text(value), styles['contact']))
    for section in data['sections']:
        if not section['content'].strip():
            continue
        heading = section['title'].upper()
        label_width = min(pdfmetrics.stringWidth(heading, 'ResumeSansBold', 12) + 14, (document.width - 12) * .78)
        row = Table([[Paragraph(safe_text(heading), styles['heading']), HRFlowable(width='100%', thickness=.7, color=colors.black)]],
                    colWidths=[label_width, document.width - 12 - label_width], spaceBefore=10, spaceAfter=6, hAlign='LEFT')
        row.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
        row.keepWithNext = True
        story.append(row)
        for text, bullet, keep_next, last in resume_section_paragraphs(section):
            paragraph = Paragraph(text, styles['bullet' if bullet else 'body'], bulletText='•' if bullet else None)
            paragraph.keepWithNext = keep_next
            story.append(paragraph)
            if last:
                story.append(Spacer(1, 2))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('ResumeSans', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawRightString(A4[0] - doc.rightMargin, .9 * cm, str(doc.page))
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    stream.seek(0)
    return stream
