# PrimeiroEmprego IA

Plataforma Flask para orientar pessoas que procuram a primeira oportunidade profissional. O projeto foi criado a partir do escopo da conversa: perfil sem preenchimento fictício, currículo enviado ou gerado, cursos oficiais, vagas com URL original e datas dinâmicas no fuso `America/Sao_Paulo`.

## Executar localmente

No PowerShell, dentro desta pasta:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Depois abra `http://127.0.0.1:5000` no navegador.

## O que está implementado

- Cadastro e login local, com senha protegida por hash e perfil inicialmente vazio.
- Perfil profissional persistido em SQLite e indicador de preenchimento.
- Currículo em PDF/DOCX: armazenamento, visualização, exclusão e análise automática de organização.
- Gerador de currículo que inclui apenas campos preenchidos pela pessoa; pré-visualização e download em PDF.
- Catálogo de instituições com links oficiais: SENAC, SENAI, EBAC e Fundação Bradesco Escola Virtual.
- Recomendações de estudo baseadas em termos que a própria pessoa informou no perfil, sem prometer emprego.
- Página de vagas preparada para exibir apenas registros que tenham URL individual HTTP(S) válida. O banco começa vazio de propósito: não há vagas nem links inventados.
- Datas criadas no backend a partir da função central `now_sp()` no fuso de São Paulo.

## Para publicar

Antes de colocar em produção, defina uma `SECRET_KEY` forte como variável de ambiente, use um servidor WSGI e troque SQLite por uma base gerenciada se houver muitos usuários.
