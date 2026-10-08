"""Build the curated first-job choices used by the profile and catalog."""
import json
from pathlib import Path

AREAS = [
    ("administracao", "Administração", "Auxiliar administrativo", ["escritório", "administrativo", "secretariado"]),
    ("financeiro", "Finanças e Contabilidade", "Auxiliar financeiro ou contábil", ["contábil", "contabilidade", "financeiro", "economia"]),
    ("comercial", "Comércio e Atendimento", "Atendente ou auxiliar de vendas", ["loja", "vendas", "comercial", "recepção", "telemarketing"]),
    ("tecnologia", "Tecnologia da Informação", "Suporte de TI júnior", ["informática", "programação", "desenvolvimento", "suporte", "TI"]),
    ("marketing", "Marketing e Comunicação", "Assistente de marketing", ["design", "publicidade", "mídias sociais", "comunicação"]),
    ("logistica", "Logística", "Auxiliar de logística ou estoque", ["estoque", "almoxarifado", "expedição", "compras"]),
    ("rh", "Recursos Humanos", "Auxiliar de recursos humanos", ["RH", "departamento pessoal", "recrutamento", "psicologia"]),
    ("industria", "Indústria e Engenharia", "Auxiliar de produção", ["produção", "qualidade", "manutenção", "engenharia", "industrial"]),
    ("saude", "Saúde", "Recepcionista de clínica", ["enfermagem", "farmácia", "saúde", "hospital", "clínica"]),
    ("educacao", "Educação e Pedagogia", "Auxiliar de sala ou apoio escolar", ["pedagogia", "educação", "escola", "infantil"]),
]


def build():
    options = [{"code": "aprendiz-geral", "title": "Jovem Aprendiz — todas as áreas de entrada", "areas": [a[0] for a in AREAS], "contract_type": "aprendiz", "aliases": ["primeiro emprego", "aprendiz", "aprendizagem"]}]
    for key, label, _, aliases in AREAS:
        if key in {"administracao", "comercial", "logistica"}:
            options.append({"code": f"aprendiz-{key}", "title": f"Jovem Aprendiz — {label}", "areas": [key], "contract_type": "aprendiz", "aliases": aliases})
    for contract, prefix in (("estagio", "Estágio"), ("clt", "CLT")):
        for key, label, role, aliases in AREAS:
            title = f"{prefix} — {label}" if contract == "estagio" else f"CLT — {role}"
            options.append({"code": f"{contract}-{key}", "title": title, "areas": [key], "contract_type": contract, "aliases": [label, *aliases]})
    path = Path(__file__).resolve().parents[1] / "static" / "occupations.json"
    path.write_text(json.dumps({"source": "Seleção de áreas de entrada em Curitiba; fontes e critérios em docs/pesquisa-oportunidades.md", "checked_on": "2026-10-08", "occupations": options}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(options)} opções em {len(AREAS)} áreas.")


if __name__ == "__main__":
    build()
