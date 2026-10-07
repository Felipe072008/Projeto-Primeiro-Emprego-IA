import json
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from contextlib import contextmanager
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template, request, send_file, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from catalog import recommendations
from resume_documents import InvalidPDF, MAX_PDF_BYTES, inspect_pdf, build_resume_pdf, text_from_resume
from resume_analysis import analyze, ai_status


BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("FIRST_JOB_DATABASE", str(BASE_DIR / "primeiro_emprego.db")))
UPLOAD_DIR = Path(os.environ.get("FIRST_JOB_UPLOAD_DIR", str(BASE_DIR / "uploads")))
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")
ALLOWED_EXTENSIONS = {"pdf"}
MAX_UPLOAD_SIZE = 8 * 1024 * 1024

app = Flask(__name__)
# Set SECRET_KEY as an environment variable in production (e.g. on PythonAnywhere's
# Web tab). Without one, a new random key is generated each time the app starts —
# safer than a fixed default, but it means active sessions are cleared on restart.
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=MAX_UPLOAD_SIZE + 64 * 1024,
)
UPLOAD_DIR.mkdir(exist_ok=True)


def now_sp() -> datetime:
    """Central source of truth for every date saved by the application."""
    return datetime.now(BRAZIL_TZ)


def date_label(value: datetime | None = None) -> str:
    return (value or now_sp()).strftime("%d/%m/%Y")


def timestamp() -> str:
    return now_sp().isoformat()


@contextmanager
def db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


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
REQUIRED_PROFILE_FIELDS = {
    "phone": "Telefone", "age": "Idade", "city": "Cidade", "state": "Estado",
    "desired_area": "Área profissional desejada", "education": "Escolaridade",
    "skills": "Habilidades", "languages": "Idiomas",
}
EDUCATION_OPTIONS = {
    "Fundamental Incompleto", "Fundamental Completo", "Médio Incompleto",
    "Médio Completo", "Cursando Ensino Médio", "Superior Incompleto",
    "Cursando Superior",
}


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


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def resume_payload(user: dict, profile: dict, supplied: dict | None = None) -> dict:
    """Creates a resume only with values supplied by the person using the platform."""
    supplied = supplied or {}

    def choose(key: str):
        value = supplied.get(key, profile.get(key, ""))
        return str(value or "").strip()

    contact_parts = []
    email = str(supplied.get("email", user["email"]) or "").strip()
    if email:
        contact_parts.append(email)
    if choose("phone"):
        contact_parts.append(choose("phone"))
    location = str(supplied.get("location", " / ".join(part for part in (choose("city"), choose("state")) if part)) or "").strip()
    if location:
        contact_parts.append(location)

    sections = [
        ("Objetivo profissional", choose("objective")),
        ("Formação acadêmica", choose("education")),
        ("Curso em andamento ou concluído", choose("course")),
        ("Experiência profissional", choose("professional_experience")),
        ("Experiências acadêmicas e projetos", choose("academic_experience")),
        ("Cursos e certificações", choose("courses")),
        ("Habilidades", choose("skills")),
        ("Idiomas", choose("languages")),
        ("Informações adicionais", choose("additional_information")),
    ]
    return {
        "name": choose("full_name") or user["name"],
        "headline": str(supplied.get("headline", profile.get("desired_area", "")) or "").strip(),
        "contacts": contact_parts,
        "sections": [{"title": title, "content": content} for title, content in sections if content],
        "created_on": date_label(),
    }


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
    if not isinstance(data, dict):
        return jsonify({"error": "Dados do perfil inválidos."}), 400
    profile_data = {field: str(data.get(field) or "").strip() for field in PROFILE_FIELDS}
    missing = [label for field, label in REQUIRED_PROFILE_FIELDS.items() if not profile_data[field]]
    if missing:
        return jsonify({"error": "Preencha os campos obrigatórios: " + ", ".join(missing) + "."}), 400
    for field, limit, label in (("phone", 11, "Telefone"), ("age", 3, "Idade")):
        value = profile_data[field]
        if len(value) > limit or not value.isascii() or not value.isdigit():
            return jsonify({"error": f"{label} deve conter apenas números, com no máximo {limit} dígitos."}), 400
    if profile_data["education"] not in EDUCATION_OPTIONS:
        return jsonify({"error": "Selecione uma das opções de escolaridade disponíveis."}), 400
    values = [profile_data[field] for field in PROFILE_FIELDS]
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
    job_count = recommendations("jobs", profile, today=now_sp().date())["total"]
    return jsonify({
        "profile_completion": profile_completion(profile),
        "resume_count": resume_count,
        "verified_job_count": job_count,
        "recommendations": [dict(item, reason=item["match_reason"]) for item in recommendations("courses", profile, today=now_sp().date())["courses"][:3]],
        "advice": profile_advice(profile),
        "today": date_label(),
    })


@app.get("/api/jobs")
@login_required
def jobs():
    return jsonify(recommendations("jobs", get_profile(current_user_id()), show_all=request.args.get("all") == "1", query=request.args.get("q", "")[:120], today=now_sp().date()))


@app.get("/api/courses")
@login_required
def courses():
    return jsonify(recommendations("courses", get_profile(current_user_id()), show_all=request.args.get("all") == "1", query=request.args.get("q", "")[:120], course_type=request.args.get("type", ""), free_only=request.args.get("free") == "1", today=now_sp().date()))


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
        return jsonify({"error": "Selecione um arquivo PDF."}), 400
    if not allowed_file(uploaded.filename):
        return jsonify({"error": "Apenas currículos em PDF são aceitos."}), 400
    content = uploaded.read(MAX_PDF_BYTES + 1)
    try:
        metadata = inspect_pdf(content)
    except InvalidPDF as exc:
        return jsonify({"error": str(exc)}), 400
    clean_name = secure_filename(uploaded.filename) or "curriculo.pdf"
    stored_name = f"{uuid.uuid4().hex}_{clean_name}"
    destination = UPLOAD_DIR / stored_name
    destination.write_bytes(content)
    try:
        with db_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO resumes (user_id, kind, original_name, saved_name, content_json, created_at, updated_at) VALUES (?, 'uploaded', ?, ?, NULL, ?, ?)",
                (current_user_id(), clean_name, stored_name, timestamp(), timestamp()),
            )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    warning = "Este PDF parece digitalizado ou tem pouco texto legível. A análise precisa de um PDF com texto selecionável." if not metadata["readable"] else ""
    return jsonify({"message": "Currículo PDF enviado com sucesso.", "warning": warning, "id": cursor.lastrowid}), 201


@app.post("/api/resumes/generate")
@login_required
def generate_resume():
    supplied = request.get_json(silent=True) or {}
    if not isinstance(supplied, dict) or any(not isinstance(value, str) or len(value) > 4000 for value in supplied.values()):
        return jsonify({"error": "Use textos de até 4.000 caracteres por campo."}), 400
    if len(str(supplied.get("full_name", ""))) > 120 or len(str(supplied.get("headline", ""))) > 160:
        return jsonify({"error": "Use um nome de até 120 caracteres e uma área de até 160 caracteres."}), 400
    user = get_user(current_user_id())
    data = resume_payload(user, get_profile(current_user_id()), supplied)
    if len(text_from_resume(data)) > 20000:
        return jsonify({"error": "O currículo está muito longo. Reduza o conteúdo para até 20 mil caracteres."}), 400
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
        data = json.loads(resume["content_json"])
        pdf = build_resume_pdf(data)
        metadata = inspect_pdf(pdf.getvalue())
        text = text_from_resume(data)
    else:
        path = UPLOAD_DIR / resume["saved_name"]
        if not path.exists():
            return jsonify({"error": "O arquivo não está mais disponível. Envie seu PDF novamente."}), 404
        try:
            metadata = inspect_pdf(path.read_bytes())
        except InvalidPDF as exc:
            return jsonify({"error": str(exc)}), 422
        text = metadata["text"]
    if not metadata["readable"]:
        return jsonify({"error": "Não há texto legível suficiente para analisar. Exporte o documento com texto selecionável; PDFs digitalizados precisam de reconhecimento de texto (OCR)."}), 422
    profile = get_profile(current_user_id())
    matching_jobs = recommendations("jobs", profile, today=now_sp().date())["jobs"]
    return jsonify(analyze(text, profile, metadata, matching_jobs, use_ai=request.args.get("mode") != "checks"))


@app.get("/api/ai/status")
@login_required
def local_ai_status():
    return jsonify(ai_status())


@app.get("/api/resumes/<int:resume_id>/pdf")
@login_required
def resume_pdf(resume_id):
    resume = owned_resume(resume_id)
    if not resume or resume["kind"] != "generated":
        return jsonify({"error": "Crie um currículo pela plataforma para baixar a versão em PDF."}), 404
    data = json.loads(resume["content_json"])
    stream = build_resume_pdf(data)
    filename = secure_filename(f"curriculo-{data['name']}.pdf")
    return send_file(stream, mimetype="application/pdf", as_attachment=request.args.get("inline") != "1", download_name=filename)



@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "O arquivo ultrapassa o limite de 8 MB."}), 413


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
