import io
import json
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template, request, send_file, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "primeiro_emprego.db"
UPLOAD_DIR = BASE_DIR / "uploads"
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_UPLOAD_SIZE = 8 * 1024 * 1024

app = Flask(__name__)
# Set SECRET_KEY as an environment variable in production (e.g. on PythonAnywhere's
# Web tab). Without one, a new random key is generated each time the app starts —
# safer than a fixed default, but it means active sessions are cleared on restart.
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=MAX_UPLOAD_SIZE,
)
UPLOAD_DIR.mkdir(exist_ok=True)


def now_sp() -> datetime:
    """Central source of truth for every date saved by the application."""
    return datetime.now(BRAZIL_TZ)


def date_label(value: datetime | None = None) -> str:
    return (value or now_sp()).strftime("%d/%m/%Y")


def timestamp() -> str:
    return now_sp().isoformat()


def db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                phone TEXT DEFAULT '',
                city TEXT DEFAULT '',
                state TEXT DEFAULT '',
                age TEXT DEFAULT '',
                education TEXT DEFAULT '',
                course TEXT DEFAULT '',
                desired_area TEXT DEFAULT '',
                professional_experience TEXT DEFAULT '',
                academic_experience TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                courses TEXT DEFAULT '',
                languages TEXT DEFAULT '',
                objective TEXT DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('uploaded', 'generated')),
                original_name TEXT,
                saved_name TEXT,
                content_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                requirements TEXT NOT NULL,
                source TEXT NOT NULL,
                original_url TEXT NOT NULL,
                published_at TEXT,
                last_updated_at TEXT
            );
            """
        )


PROFILE_FIELDS = (
    "phone", "city", "state", "age", "education", "course", "desired_area",
    "professional_experience", "academic_experience", "skills", "courses",
    "languages", "objective",
)


def profile_completion(profile: dict) -> int:
    # The user name and email are registered in the account, so they count too.
    filled = sum(bool(str(profile.get(field, "")).strip()) for field in PROFILE_FIELDS)
    return round((filled / len(PROFILE_FIELDS)) * 100)


def get_user(user_id: int):
    with db_connection() as connection:
        row = connection.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def get_profile(user_id: int) -> dict:
    with db_connection() as connection:
        row = connection.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {field: "" for field in PROFILE_FIELDS}
    return dict(row)


def current_user_id():
    return session.get("user_id")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user_id():
            return jsonify({"error": "Faça login para continuar."}), 401
        return view(*args, **kwargs)

    return wrapped


def valid_external_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except (TypeError, ValueError):
        return False


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def resume_payload(user: dict, profile: dict, supplied: dict | None = None) -> dict:
    """Creates a resume only with values supplied by the person using the platform."""
    supplied = supplied or {}

    def choose(key: str):
        value = supplied.get(key, profile.get(key, ""))
        return str(value or "").strip()

    contact_parts = [user["email"]]
    if choose("phone"):
        contact_parts.append(choose("phone"))
    location = " / ".join(part for part in (choose("city"), choose("state")) if part)
    if location:
        contact_parts.append(location)

    sections = [
        ("Objetivo profissional", choose("objective")),
        ("Formação acadêmica", choose("education")),
        ("Experiência profissional", choose("professional_experience")),
        ("Experiências acadêmicas e projetos", choose("academic_experience")),
        ("Cursos e certificações", choose("courses")),
        ("Habilidades", choose("skills")),
        ("Idiomas", choose("languages")),
        ("Informações adicionais", choose("additional_information")),
    ]
    return {
        "name": choose("full_name") or user["name"],
        "contacts": contact_parts,
        "sections": [{"title": title, "content": content} for title, content in sections if content],
        "created_on": date_label(),
    }


def generated_resume_analysis(data: dict) -> list[dict]:
    sections = {item["title"].lower(): item["content"] for item in data.get("sections", [])}
    feedback = []
    for name, label in (
        ("objetivo profissional", "objetivo profissional"),
        ("formação acadêmica", "formação acadêmica"),
        ("habilidades", "habilidades"),
    ):
        if name in sections:
            feedback.append({"type": "positive", "text": f"Seu currículo já apresenta {label}."})
        else:
            feedback.append({"type": "attention", "text": f"Inclua {label} se essa informação fizer sentido para você."})
    if "experiência profissional" not in sections:
        feedback.append({
            "type": "tip",
            "text": "Não há experiência profissional informada. Valorize formação, cursos e projetos reais — sem inventar experiências.",
        })
    return feedback


def extract_document_text(path: Path) -> str:
    """Best-effort extraction used only to point out visible/missing resume sections."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            from pypdf import PdfReader

            return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        if suffix == ".docx":
            from docx import Document

            return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    except Exception:
        return ""
    return ""


def uploaded_resume_analysis(path: Path) -> list[dict]:
    text = extract_document_text(path).lower()
    if not text:
        return [{
            "type": "tip",
            "text": "Não foi possível ler o texto automaticamente. Você ainda pode visualizar ou substituir o arquivo; um PDF/DOCX com texto selecionável melhora a análise.",
        }]

    targets = (
        ("objetivo", "objetivo profissional"),
        ("forma", "formação"),
        ("experi", "experiência"),
        ("habil", "habilidades"),
        ("curso", "cursos"),
    )
    feedback = []
    for token, label in targets:
        if token in text:
            feedback.append({"type": "positive", "text": f"Identificamos uma seção relacionada a {label}."})
        else:
            feedback.append({"type": "attention", "text": f"Considere deixar {label} mais explícito, caso essa informação exista."})
    return feedback


def course_recommendations(profile: dict) -> list[dict]:
    source = " ".join(
        str(profile.get(key, "")).lower()
        for key in ("desired_area", "objective", "skills", "course")
    )
    rules = [
        (("administra", "escritório", "financeir", "excel"), "Excel e ferramentas de escritório", "Pode apoiar rotinas administrativas e organização de informações."),
        (("tecnolog", "program", "sistema", "informática"), "Lógica de programação", "Ajuda a construir uma base para áreas de tecnologia."),
        (("atendimento", "vendas", "comercial", "comunica"), "Comunicação profissional e atendimento", "Pode fortalecer a comunicação em processos seletivos e no atendimento."),
        (("design", "marketing", "social media"), "Comunicação visual e marketing digital", "É uma área de estudo relacionada ao interesse informado no seu perfil."),
        (("logística", "estoque", "almoxarifado"), "Fundamentos de logística", "Pode complementar conhecimentos para vagas de operações e logística."),
    ]
    found = []
    for terms, title, reason in rules:
        if any(term in source for term in terms):
            found.append({"title": title, "reason": reason})
    return found[:3]


def profile_advice(profile: dict) -> dict:
    completion = profile_completion(profile)
    info = []
    if profile.get("desired_area"):
        info.append(f"área desejada: {profile['desired_area']}")
    if profile.get("skills"):
        info.append("habilidades informadas")
    if profile.get("education"):
        info.append("formação informada")

    next_steps = []
    if not profile.get("objective"):
        next_steps.append("Escreva um objetivo profissional curto e focado na área que você procura.")
    if not profile.get("skills"):
        next_steps.append("Liste habilidades reais, inclusive conhecimentos adquiridos na escola, cursos ou projetos.")
    if not profile.get("academic_experience") and not profile.get("professional_experience"):
        next_steps.append("Se não possui experiência profissional, descreva projetos acadêmicos, trabalhos voluntários ou atividades que você realmente realizou.")
    if not next_steps:
        next_steps.append("Seu perfil já tem informações suficientes para gerar e revisar seu currículo.")

    return {
        "completion": completion,
        "basis": info or ["ainda não há informações profissionais preenchidas"],
        "next_steps": next_steps,
    }


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/meta")
def meta():
    return jsonify({"date": date_label(), "timezone": "America/Sao_Paulo"})


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not name or not email or len(password) < 6:
        return jsonify({"error": "Informe nome, e-mail e uma senha com pelo menos 6 caracteres."}), 400
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "Informe um e-mail válido."}), 400
    try:
        with db_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(password), timestamp()),
            )
            user_id = cursor.lastrowid
            values = [user_id, timestamp()] + [""] * len(PROFILE_FIELDS)
            columns = "user_id, updated_at, " + ", ".join(PROFILE_FIELDS)
            placeholders = ", ".join("?" for _ in values)
            connection.execute(f"INSERT INTO profiles ({columns}) VALUES ({placeholders})", values)
    except sqlite3.IntegrityError:
        return jsonify({"error": "Já existe uma conta com este e-mail."}), 409
    session.clear()
    session["user_id"] = user_id
    return jsonify({"message": "Conta criada. Agora complete seu perfil profissional.", "user": get_user(user_id)}), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    with db_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "E-mail ou senha incorretos."}), 401
    session.clear()
    session["user_id"] = row["id"]
    return jsonify({"message": "Login realizado.", "user": get_user(row["id"])})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"message": "Você saiu da sua conta."})


@app.get("/api/me")
def me():
    user_id = current_user_id()
    if not user_id:
        return jsonify({"authenticated": False})
    user = get_user(user_id)
    if not user:
        session.clear()
        return jsonify({"authenticated": False})
    profile = get_profile(user_id)
    return jsonify({
        "authenticated": True,
        "user": user,
        "profile": profile,
        "completion": profile_completion(profile),
    })


@app.route("/api/profile", methods=["GET", "PUT"])
@login_required
def profile():
    user_id = current_user_id()
    if request.method == "GET":
        return jsonify({"user": get_user(user_id), "profile": get_profile(user_id)})

    data = request.get_json(silent=True) or {}
    values = [str(data.get(field, "")).strip() for field in PROFILE_FIELDS]
    with db_connection() as connection:
        connection.execute(
            "UPDATE profiles SET " + ", ".join(f"{field} = ?" for field in PROFILE_FIELDS) + ", updated_at = ? WHERE user_id = ?",
            values + [timestamp(), user_id],
        )
    saved = get_profile(user_id)
    return jsonify({"message": "Perfil salvo.", "profile": saved, "completion": profile_completion(saved)})


@app.get("/api/dashboard")
@login_required
def dashboard():
    user_id = current_user_id()
    profile = get_profile(user_id)
    with db_connection() as connection:
        resume_count = connection.execute("SELECT COUNT(*) FROM resumes WHERE user_id = ?", (user_id,)).fetchone()[0]
        job_count = connection.execute(
            "SELECT COUNT(*) FROM jobs WHERE original_url LIKE 'http%'"
        ).fetchone()[0]
    return jsonify({
        "profile_completion": profile_completion(profile),
        "resume_count": resume_count,
        "verified_job_count": job_count,
        "recommendations": course_recommendations(profile),
        "advice": profile_advice(profile),
        "today": date_label(),
    })


@app.get("/api/jobs")
@login_required
def jobs():
    with db_connection() as connection:
        rows = connection.execute("SELECT * FROM jobs ORDER BY COALESCE(last_updated_at, '') DESC").fetchall()
    # A job with no individual HTTP(S) URL is deliberately withheld from the public list.
    verified = [dict(row) for row in rows if valid_external_url(row["original_url"])]
    return jsonify({"jobs": verified, "updated_on": date_label()})


@app.get("/api/courses")
@login_required
def courses():
    institutions = [
        {"name": "SENAC", "description": "Cursos profissionalizantes, técnicos e de capacitação.", "url": "https://www.senac.br/"},
        {"name": "SENAI", "description": "Formação profissional para a indústria e tecnologia.", "url": "https://www.senai.br/"},
        {"name": "EBAC", "description": "Cursos online em áreas criativas, tecnologia e negócios.", "url": "https://ebaconline.com.br/"},
        {"name": "Fundação Bradesco Escola Virtual", "description": "Cursos gratuitos online para desenvolvimento profissional.", "url": "https://www.ev.org.br/"},
    ]
    return jsonify({"institutions": institutions, "recommendations": course_recommendations(get_profile(current_user_id()))})


@app.post("/api/advice")
@login_required
def advice():
    return jsonify(profile_advice(get_profile(current_user_id())))


@app.get("/api/resumes")
@login_required
def list_resumes():
    with db_connection() as connection:
        rows = connection.execute(
            "SELECT id, kind, original_name, created_at, updated_at FROM resumes WHERE user_id = ? ORDER BY updated_at DESC",
            (current_user_id(),),
        ).fetchall()
    return jsonify({"resumes": [dict(row) for row in rows]})


@app.post("/api/resumes/upload")
@login_required
def upload_resume():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Selecione um arquivo PDF ou DOCX."}), 400
    if not allowed_file(uploaded.filename):
        return jsonify({"error": "Envie um arquivo em PDF ou DOCX."}), 400
    clean_name = secure_filename(uploaded.filename)
    stored_name = f"{uuid.uuid4().hex}_{clean_name}"
    destination = UPLOAD_DIR / stored_name
    uploaded.save(destination)
    with db_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO resumes (user_id, kind, original_name, saved_name, content_json, created_at, updated_at) VALUES (?, 'uploaded', ?, ?, NULL, ?, ?)",
            (current_user_id(), clean_name, stored_name, timestamp(), timestamp()),
        )
    return jsonify({"message": "Currículo enviado com sucesso.", "id": cursor.lastrowid}), 201


@app.post("/api/resumes/generate")
@login_required
def generate_resume():
    supplied = request.get_json(silent=True) or {}
    user = get_user(current_user_id())
    data = resume_payload(user, get_profile(current_user_id()), supplied)
    if not data["sections"]:
        return jsonify({"error": "Preencha ao menos uma informação profissional antes de criar seu currículo."}), 400
    with db_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO resumes (user_id, kind, original_name, saved_name, content_json, created_at, updated_at) VALUES (?, 'generated', NULL, NULL, ?, ?, ?)",
            (current_user_id(), json.dumps(data, ensure_ascii=False), timestamp(), timestamp()),
        )
    return jsonify({"message": "Currículo criado com suas informações.", "id": cursor.lastrowid, "resume": data}), 201


def owned_resume(resume_id: int):
    with db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM resumes WHERE id = ? AND user_id = ?", (resume_id, current_user_id())
        ).fetchone()
    return dict(row) if row else None


@app.get("/api/resumes/<int:resume_id>")
@login_required
def get_resume(resume_id):
    resume = owned_resume(resume_id)
    if not resume:
        return jsonify({"error": "Currículo não encontrado."}), 404
    if resume["kind"] == "generated":
        resume["content"] = json.loads(resume["content_json"])
    return jsonify(resume)


@app.get("/api/resumes/<int:resume_id>/file")
@login_required
def resume_file(resume_id):
    resume = owned_resume(resume_id)
    if not resume or resume["kind"] != "uploaded":
        return jsonify({"error": "Arquivo não encontrado."}), 404
    path = UPLOAD_DIR / resume["saved_name"]
    if not path.exists():
        return jsonify({"error": "O arquivo não está mais disponível."}), 404
    return send_file(path, download_name=resume["original_name"], as_attachment=False)


@app.delete("/api/resumes/<int:resume_id>")
@login_required
def delete_resume(resume_id):
    resume = owned_resume(resume_id)
    if not resume:
        return jsonify({"error": "Currículo não encontrado."}), 404
    if resume["saved_name"]:
        path = UPLOAD_DIR / resume["saved_name"]
        if path.exists():
            path.unlink()
    with db_connection() as connection:
        connection.execute("DELETE FROM resumes WHERE id = ? AND user_id = ?", (resume_id, current_user_id()))
    return jsonify({"message": "Currículo excluído."})


@app.post("/api/resumes/<int:resume_id>/analyze")
@login_required
def analyze_resume(resume_id):
    resume = owned_resume(resume_id)
    if not resume:
        return jsonify({"error": "Currículo não encontrado."}), 404
    if resume["kind"] == "generated":
        feedback = generated_resume_analysis(json.loads(resume["content_json"]))
    else:
        feedback = uploaded_resume_analysis(UPLOAD_DIR / resume["saved_name"])
    return jsonify({
        "message": "Análise concluída apenas a partir das informações encontradas no seu currículo.",
        "feedback": feedback,
    })


@app.get("/api/resumes/<int:resume_id>/pdf")
@login_required
def resume_pdf(resume_id):
    resume = owned_resume(resume_id)
    if not resume or resume["kind"] != "generated":
        return jsonify({"error": "Crie um currículo pela plataforma para baixar a versão em PDF."}), 404
    try:
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError:
        return jsonify({"error": "A geração de PDF requer a dependência reportlab. Execute pip install -r requirements.txt."}), 503

    data = json.loads(resume["content_json"])
    stream = io.BytesIO()
    document = SimpleDocTemplate(stream, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1.7 * cm, bottomMargin=1.7 * cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ResumeName", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=HexColor("#163A5F"), spaceAfter=6))
    styles.add(ParagraphStyle(name="ResumeContact", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=HexColor("#4B5563"), spaceAfter=16))
    styles.add(ParagraphStyle(name="ResumeHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=HexColor("#163A5F"), spaceBefore=11, spaceAfter=4))
    styles.add(ParagraphStyle(name="ResumeBody", parent=styles["Normal"], fontSize=10, leading=14, textColor=HexColor("#202938")))
    story = [Paragraph(data["name"].upper(), styles["ResumeName"]), Paragraph(" • ".join(data["contacts"]), styles["ResumeContact"])]
    for section in data["sections"]:
        safe_text = section["content"].replace("\n", "<br/>")
        story.extend([Paragraph(section["title"].upper(), styles["ResumeHeading"]), Paragraph(safe_text, styles["ResumeBody"])])
    story.append(Spacer(1, 12))
    document.build(story)
    stream.seek(0)
    filename = secure_filename(f"curriculo-{data['name'].lower().replace(' ', '-')}.pdf")
    return send_file(stream, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "O arquivo ultrapassa o limite de 8 MB."}), 413


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
