"""Apresentação compartilhada pelas versões históricas, prévia e PDF."""
import re
from urllib.parse import urlsplit

PALETTE = {
    "marinho": ("Azul-marinho", "#0F2942"), "azul": ("Azul", "#0369A1"),
    "verde": ("Verde", "#166534"), "vinho": ("Vinho", "#7F1D1D"),
    "grafite": ("Grafite", "#1F2937"), "roxo": ("Roxo", "#5B21B6"),
}
EDUCATION = "Formação acadêmica"
EXPERIENCE = "Experiências e atividades relevantes"
COURSES = "Cursos complementares e certificações"
SKILLS = "Habilidades e competências"
ADDITIONAL = "Informações adicionais"
OBJECTIVE = "Objetivo profissional"
LABELS = {"Habilidades": "Habilidades", "Conhecimentos Técnicos": "Conhecimentos Técnicos",
          "Competências Comportamentais": "Competências Comportamentais", "Idiomas": "Idiomas"}
GROUPS = {"Curso em andamento ou concluído": EDUCATION, "Experiência profissional": EXPERIENCE,
          "Experiências acadêmicas e projetos": EXPERIENCE, "Cursos e certificações": COURSES,
          **dict.fromkeys(LABELS, SKILLS)}


def accent_id(value):
    return value if isinstance(value, str) and value in PALETTE else "marinho"


def valid_link(value):
    if not isinstance(value, str) or len(value) > 500 or re.search(r'[\s\\<>"\'\x00-\x1f\x7f]', value):
        return False
    try:
        url = urlsplit(value)
        return url.scheme in ("https", "http") and bool(url.hostname) and url.username is None and url.port != 0
    except ValueError:
        return False


def objective_for(mode, area, course):
    area = f" na área de {area}" if area else ""
    if mode == "Estágio":
        learning = f"aplicar os conhecimentos adquiridos no curso de {course} e " if course else ""
        return f"Busco oportunidade de Estágio{area}, visando {learning}desenvolver minhas habilidades profissionais."
    if mode == "Jovem Aprendiz":
        return ("Busco oportunidade como Jovem Aprendiz para iniciar minha trajetória profissional, "
                "contribuindo com dedicação, facilidade de aprendizado e trabalho em equipe.")
    if mode == "CLT":
        return f"Busco minha primeira oportunidade efetiva (CLT){area}, com foco em crescimento profissional e entrega de resultados."
    return ""


def line(text="", *, bold="", detail="", bullet=False):
    return dict(text=text, bold=bold, detail=detail, bullet=bullet)


def record(group, title, content):
    lines = content.splitlines()
    first, *rest = lines
    if title in LABELS:
        return [line(" " + content, bold=LABELS[title] + ":", bullet=True)]
    if group in (EDUCATION, EXPERIENCE, COURSES):
        separator = " | " if group == EXPERIENCE else " — "
        head, sep, tail = first.partition(separator)
        if not sep and group == EXPERIENCE:
            head, sep, tail = first.partition(" — ")
        if not sep:
            head, sep, tail = first.partition(" · ")
        details = ""
        if group == COURSES:
            tail, paren, extra = tail.partition(" (")
            if paren:
                details = paren + extra
        result = [line(separator + tail if sep else "", bold=head, detail=details, bullet=group == COURSES)]
        for value in rest:
            if group == EXPERIENCE:
                # Período gravado pelo formatador antigo de experiências.
                period = re.fullmatch(r'(\d{2}/\d{2}/\d{4}) a (atualmente|término não informado|\d{2}/\d{2}/\d{4})', value)
                if period:
                    start, end = period.groups()
                    end = "Atual" if end == "atualmente" else "" if end == "término não informado" else end
                    value = " – ".join(filter(None, [start, end]))
            if group == EDUCATION and value.startswith("Status: "):
                result.append(line(bold="Status:", detail=" " + value[8:]))
            else:
                result.append(line(value))
        return result
    return [line(content)]


def presentation(data):
    contacts = [[], [], []]
    for value in data.get("contacts", []):
        value = value.strip()
        if not value or value.casefold() == "não informado":
            continue
        if re.fullmatch(r'(?:\d{10,11}|\(\d{2}\) ?\d{4,5}-\d{4})', value):
            contacts[1].append(re.sub(r'^(\d{2})(\d{4,5})(\d{4})$', r'(\1) \2-\3', value))
        elif "@" in value:
            contacts[2].append(value)
        else:
            contacts[0].append(re.sub(r" / ([^/]+)$", r" - \1", value))
    groups = {title: [] for title in (OBJECTIVE, EDUCATION, EXPERIENCE, COURSES, SKILLS)}
    additional = []
    for section in data.get("sections", []):
        title = section["title"].strip()
        if not title:
            continue
        group = GROUPS.get(title, title)
        for part in re.split(r'\n\s*\n', section["content"].strip()):
            if part.strip() and part.strip().casefold() != "não informado":
                dest = additional if group == ADDITIONAL else groups.setdefault(group, [])
                dest.append(record(group, title, part.strip()))
    groups[ADDITIONAL] = additional
    return dict(name=data["name"].upper(), headline=data.get("headline", "").strip(), contact=" | ".join(v for part in contacts for v in part),
                link=data.get("link") if valid_link(data.get("link")) else "",
                accent=accent_id(data.get("accent")), color=PALETTE[accent_id(data.get("accent"))][1],
                sections=[dict(title=k.upper(), records=v) for k, v in groups.items() if v])

