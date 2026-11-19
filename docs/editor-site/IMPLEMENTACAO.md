# Editor visual

## Versão com canvas

Consulte o [guia do administrador](COMO_USAR.md) e o [catálogo de elementos e limites](CATALOGO.md). O roteiro de atualização no PythonAnywhere está neste documento, na seção **Aplicar no PythonAnywhere**.

Arquivos da versão com canvas, relativos à raiz do repositório:

| Parte | Arquivos |
|---|---|
| Servidor | `admin.py`, `canvas_login.py`, `conteudo_editavel.py`, `editor_site.py` |
| Editor | `templates/canvas_login.html`, `admin_assets/canvas_login.css`, `admin_assets/canvas_login.js`, `admin_assets/editor_site.js` |
| Site público | `templates/pagina_principal.html`, `static/conteudo_site.css`, `static/interface_site.js`, `static/layout_visual.js` |
| Testes | `tests/test_editor_site.py`, `tests/verificar_canvas_login.py`, `tests/verificar_editor_site.py` |
| Documentação | `docs/editor-site/CATALOGO.md`, `docs/editor-site/COMO_USAR.md`, `docs/editor-site/IMPLEMENTACAO.md` |

## Registro histórico da primeira versão — 18/11/2026

Projeto confirmado no VS Code: `C:\Users\felip\Documents\primeiro-emprego-ia`, branch `atualizar-primeiro-emprego-ia`. A árvore estava limpa antes desta tarefa. Nenhum deploy ou publicação no servidor foi executado. As publicações dos testes usaram bancos temporários.

## Arquivos completos

Todos os caminhos abaixo são relativos à raiz confirmada:

| Arquivo | Entrega |
|---|---|
| `conteudo_editavel.py` | Catálogo fechado, padrões, tipos, tamanhos, URLs, contraste e resumo das mudanças |
| `editor_site.py` | Migração, rascunho/publicado, cache, renderização, CSS, logos e rotas administrativas |
| `app.py` | Migração idempotente e registro das rotas públicas |
| `admin.py` | Reutiliza sessão/CSRF/auditoria; libera somente os dois novos assets autenticados |
| `requirements.txt` | Declara Pillow, já disponível como dependência do ReportLab neste ambiente; gratuita e local |
| `templates/admin.html` | Acesso “Editar site” na navegação administrativa |
| `templates/editor_site.html` | Barra de ferramentas, inspetor e prévia isolada |
| `templates/pagina_principal.html` | Textos, seções e slots marcados; CSS público do conteúdo |
| `templates/parciais/minha_conta.html` | Marcação do cabeçalho e slot; formulários travados |
| `admin_assets/editor_site.js` | Editor, histórico local, edição no lugar, tema, estrutura e blocos |
| `admin_assets/editor_site.css` | Layout do editor integrado ao painel, desktop/celular |
| `static/conteudo_site.css` | Aparência dos blocos, quebras de linha, seções ocultas e logo |
| `tests/test_editor_site.py` | Validação, segurança, versões, migração, isolamento e limites persistidos |
| `tests/verificar_editor_site.py` | Fluxo real em Chrome com bancos e arquivos descartáveis |
| `docs/editor-site/CATALOGO.md` | O que pode ser editado em cada página e limites |
| `docs/editor-site/IMPLEMENTACAO.md` | Este roteiro |

## Como funciona

- A aba administrativa abre `/admin/site`. Editor e assets exigem a mesma sessão do painel; escritas exigem o mesmo CSRF e a proteção de origem/cabeçalho existente.
- Banco principal: tabelas `site_theme`, `site_texts`, `site_layout`, `site_blocks`, cada uma com linhas `draft`/`published`; `site_versions` armazena cópias completas das últimas 30 versões publicadas. A migração só cria tabelas, sem remover ou reescrever usuários/perfis/currículos. `admin.db` continua contendo autenticação e auditoria.
- Um rascunho compartilhado pelo único administrador. A revisão por hash impede uma aba antiga de sobrescrever o rascunho salvo por outra. Desfazer/Refazer local mantém até 50 passos enquanto a página está aberta. Rascunho persistido sobrevive ao reinício.
- Salvar não publica. Publicar salva o rascunho local, apresenta os grupos alterados, nota opcional e confirmação de contraste insuficiente. Restaurar histórico/original só prepara rascunho. “Desfazer última publicação” publica uma cópia da versão anterior e também cria histórico.
- A resposta HTML pública já chega com os textos, ordem, visibilidade e blocos publicados. Não há aplicação tardia via JS, nem código do editor nos scripts públicos. `/api/site-content` é somente leitura do publicado. CSS gerado em `/site-theme.css`, com ETag/revalidação; valores validados, sem CSS digitado. Cache de conteúdo no processo detecta alterações no SQLite/WAL feitas por outros workers.
- A prévia reutiliza o HTML, remove scripts, desativa formulários/navegação e usa exemplos fixos. Não consulta banco de usuários, API de conta, currículo ou catálogo. O iframe tem sandbox sem permissão de scripts ou formulários. O CSS da prévia é gerado no servidor e entregue por Blob/link, nunca como estilo digitado pelo admin.
- Textos e blocos são escapados no servidor; o editor usa `textContent` e nós DOM, sem `innerHTML`. A inserção do documento no iframe usa exclusivamente o HTML validado/renderizado pelo servidor. HTML digitado aparece como texto. Markdown/negrito/itálico opcionais foram omitidos para manter o campo como texto simples.
- PNG/JPEG/WEBP até 1 MB: assinatura, término/tamanho do container, decodificação completa, máximo de 4 milhões de pixels e imagem estática. Recodificação em PNG remove metadados/conteúdo extra; SVG e arquivos com dados anexados são recusados. Logo tem nome aleatório e alt obrigatório. A rota pública só serve o logo publicado, como `image/png`, com `nosniff`; logos de rascunho exigem admin. Se o arquivo publicado desaparecer, a marca original volta como fallback.
- Uploads e publicações/desfazer: até 10 por IP em 10 minutos, em `request_limits` do banco principal. Janela fixa iniciada na primeira chamada; registros vencidos são limpos na próxima operação. Tentativas inválidas de upload também contam. Confiança no IP do proxy usa a configuração existente `ADMIN_TRUST_PYTHONANYWHERE`.
- Auditoria registra mutações, nunca leituras do editor. Rascunho gera no máximo um evento por sessão administrativa; os demais eventos registram publicar/restaurar/desfazer/troca de logo, sem conteúdo dos campos. O identificador do evento de rascunho é o hash não reutilizável da sessão, não o cookie/token.
- CSP pública mantém `script-src 'self'`, sem `unsafe-inline` em scripts. Estilos inline legados continuam permitidos no site público para preservar o progresso/modais existentes. No editor, scripts só locais e estilos externos/Blob; nenhum script roda na prévia.

## Verificação

Suíte completa: 101 testes Python aprovados. Inclui 7 testes novos com cenários múltiplos: chaves/limites, campos inválidos, XSS, javascript/data/rotas não permitidas, SVG, arquivo falso/poliglota/anexado/grande, alt, privacidade de logos, ausência de dados reais e consultas ao banco de usuários na prévia, CSRF, seções travadas, invisibilidade de rascunho, conflito entre abas, contraste, publicar/desfazer/restaurar, retenção de 30 versões, fallback, migração idempotente e limites persistidos de upload/publicação.

Regressões existentes de JavaScript e Chrome do administrador e privacidade aprovadas. Novo teste Chrome: texto no lugar, cor, fonte, upload de logo, ocultar/reordenar seções, cada tipo de bloco, confirmação/publicação, HTML público e desfazer. Desktop 1440px e celular 390px, sem rolagem horizontal no editor. Evidências descartáveis em `tmp/verificacao_editor/`, ignoradas pelo Git. O verificador visual estático não resolve os links Jinja `url_for`; seus alertas não substituem a conferência do Chrome.

Python instalado: 3.14. Sintaxe verificada com gramática 3.10; execução real em 3.10 não realizada. Não houve teste de carga, leitor de tela, auditoria de invasão, validação de configuração/quotas no servidor ou deploy.

## Aplicar no PythonAnywhere

1. Revise e envie o commit para a branch que o servidor usa. No servidor, ative o virtualenv já configurado em Web, entre no repositório e confirme `git status`. Preserve alterações locais antes de atualizar; não use reset/clean para descartá-las. Configure no console os mesmos caminhos de banco/uploads usados pelo WSGI.
2. Antes de importar a nova versão, faça backup dos bancos e uploads, incluindo `uploads/site-logos/`. Pause edições/uploads/exclusões durante o backup para manter as cópias coerentes. Execute no diretório do projeto:

```bash
python - <<'PY'
import os, sqlite3, tarfile
from pathlib import Path
from datetime import datetime
root = Path.cwd()
backup = Path.home() / 'backups-primeiroemprego' / datetime.now().strftime('%Y%m%d-%H%M%S')
backup.mkdir(parents=True, mode=0o700)
for name, env, default in [('principal.db','FIRST_JOB_DATABASE','primeiro_emprego.db'),
                           ('admin.db','FIRST_JOB_ADMIN_DATABASE','admin.db'),
                           ('catalogo.db','FIRST_JOB_CATALOG_DATABASE','data/catalogo_sync.db')]:
    path = Path(os.environ.get(env, root/default)).resolve()
    if path.is_file():
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as source, sqlite3.connect(backup/name) as target:
            source.backup(target)
uploads = Path(os.environ.get('FIRST_JOB_UPLOAD_DIR', root/'uploads'))
if uploads.is_dir():
    with tarfile.open(backup/'uploads.tar.gz','w:gz') as archive:
        archive.add(uploads, arcname='uploads')
print('Backup salvo em:', backup)
PY
```

3. Com a branch correta e árvore limpa, execute:

```bash
git pull --ff-only
python -m pip install -r requirements.txt
python -c "import app; app.init_db(); print('Migração concluída')"
```

A migração também roda na inicialização, mas o comando permite conferir erros antes do Reload. Não altera WSGI nem cria outro administrador. Preserve as configurações e segredos existentes. Não mapeie `admin_assets/` ou `uploads/` como diretórios estáticos públicos; devem passar pelas rotas protegidas/próprias.

4. Clique **Web → Reload**. Entre no administrador existente, abra **Editar site**, salve um rascunho e confira que o público permanece igual. Publique somente após revisar a prévia; confira numa aba pública. Os testes locais não publicaram tema ou conteúdo no seu banco real.

## Suposições e limites operacionais

- O catálogo inicial é deliberadamente conservador: textos de apresentação; dados dinâmicos e instruções de segurança ficam travados. Cada página tem um slot final, sem livre movimentação de elementos. Páginas legais permanecem fora do editor e com o visual/cópia atuais.
- A comparação de contraste exigida usa as cores de texto/fundo escolhidas. Não garante contraste de todo botão, imagem ou combinação de cores; revise a prévia ao personalizar.
- Arquivos de logo são preservados para não quebrar rascunhos/versões. Uploads abandonados e logos de versões já removidas não têm coleta automática; acompanhe espaço em disco e mantenha backups antes de limpeza operacional. O limite por tempo não substitui a quota de armazenamento do servidor.
- O conteúdo inválido/ausente usa os padrões do código. Isso não recupera um SQLite inteiro danificado nem substitui backup. Logs administrativos não são imutáveis contra quem controla os arquivos do servidor.
