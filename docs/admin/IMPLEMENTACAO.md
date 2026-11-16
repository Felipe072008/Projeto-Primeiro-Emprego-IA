# Administração do PrimeiroEmprego IA

Implementação local de 16/11/2026, na branch `atualizar-primeiro-emprego-ia`, no projeto confirmado no VS Code: `C:\Users\felip\Documents\primeiro-emprego-ia`.

## Arquivos entregues

Todos os arquivos estão completos no repositório; não é necessário copiar trechos deste documento para montá-los.

| Caminho | Alteração |
| --- | --- |
| `admin.py` | Blueprint, banco isolado, autenticação, auditoria, proteções e APIs administrativas. |
| `administracao_dados.py` | Migrações aditivas, espelho do catálogo e decisões persistidas de ocultação/remoção. |
| `create_admin.py` | Criação interativa da única conta administrativa, sem argumentos com credenciais. |
| `app.py` | Registro do Blueprint, migração, status dos usuários, último login e revogação de sessões. |
| `catalogo_oportunidades.py` | Aplica controles administrativos sem alterar os arquivos do acervo. |
| `sincronizacao_catalogo.py` | Recibo `sync_status` na transação da rotina existente. |
| `templates/admin.html` | Página administrativa própria e protegida. |
| `admin_assets/admin.js` | Interface do painel, servida somente após autenticação. |
| `admin_assets/admin.css` | Estilos do painel, com variáveis do site e telas móveis. |
| `templates/parciais/acesso_admin.html` | Botão da chave e dois modais de acesso. |
| `static/acesso_admin.js` | Apenas o fluxo público de autenticação; não contém código do painel ou credenciais. |
| `static/acesso_admin.css` | Aparência do botão e modais públicos. |
| `templates/pagina_principal.html` | Inclusão do acesso restrito abaixo do formulário de login. |
| `templates/politica_de_privacidade.html` | Informação factual sobre metadados e registros administrativos. |
| `templates/politica_cookies.html` | Inventário do cookie administrativo necessário. |
| `.gitignore` | Inclui arquivos auxiliares SQLite; bancos e uploads continuam ignorados. |
| `tests/test_admin.py` | Segurança, isolamento, migrações, privacidade, revogação e integração com importação. |
| `tests/verificar_admin.py` | Chrome local: teclado, autenticação, painel e telas móveis, com dados temporários. |
| `tests/verificar_privacidade.py` | Isola também o banco administrativo durante o teste existente. |
| `docs/admin/IMPLEMENTACAO.md` | Este roteiro, decisões e limites. |
| `README.md` | Link para este roteiro. |

Nenhuma dependência foi adicionada. `requirements.txt` permanece igual. Os arquivos do acervo, o adaptador Jooble e o workflow do GitHub Actions foram preservados.

## Comportamento e decisões

- PIN de seis dígitos validado no servidor, com autorização de cinco minutos; login administrativo com usuário e senha em seguida. Respostas de autenticação sempre genéricas.
- Cinco erros de PIN, login ou confirmação de senha por IP em 15 minutos bloqueiam novas tentativas por 15 minutos a partir do quinto erro. Tentativas, bloqueios e sessões ficam no `admin.db`; reiniciar o processo não limpa o bloqueio.
- Uma conta administrativa, criada exclusivamente pelo console. Senha de 12 a 256 caracteres. PIN e senha são hashes Werkzeug; o script não os imprime. Não existe rota de cadastro administrativo.
- Cookie próprio `peia_admin`, opaco, `Secure`, `HttpOnly`, `SameSite=Strict`. O servidor guarda apenas o hash do identificador, com CSRF separado e expiração após 30 minutos de inatividade. A etapa de PIN expira em cinco minutos. Logout revoga a sessão no banco; trocar credenciais revoga todas as sessões administrativas.
- O cookie é necessário e só é criado ao iniciar o acesso restrito. Não depende de autorização para cookies opcionais.
- HTML, JavaScript e CSS do painel ficam atrás do decorador de autenticação. Não configure mapeamento estático público para `admin_assets/`, bancos, uploads ou raiz do projeto no PythonAnywhere.
- Sem ProxyFix global: `X-Forwarded-For` é ignorado. Somente quando `ADMIN_TRUST_PYTHONANYWHERE=1`, configurado pelo operador no WSGI, usa-se `X-Real-IP`, que o balanceador do PythonAnywhere define. Fora desse ambiente, mantém-se `remote_addr`. Referência: [documentação oficial do PythonAnywhere](https://help.pythonanywhere.com/pages/WebAppClientIPAddresses/).
- CSRF por token nas alterações administrativas, além da proteção de origem/cabeçalho já existente. Jinja escapa o HTML e o painel usa `textContent`, sem inserir nomes/e-mails como HTML.
- O admin recebe nome, e-mail, datas, status, porcentagem do perfil, contagens e metadados de arquivos. Não recebe conteúdo do perfil, nome original de arquivo, caminho interno, texto extraído ou conteúdo do currículo. Não foi criada rota administrativa de visualização/download de currículo.
- Currículo enviado: tamanho do PDF armazenado. Gerado: tamanho do JSON armazenado, claramente identificado; não se inventa o tamanho de um PDF que só é gerado no download.
- Listas de usuários/currículos e históricos exibem até 200 registros. Usuários podem ser localizados por busca e status; o limite é informado na tela.
- Desativação e reativação mudam a versão das sessões do usuário. Um cookie antigo não volta a funcionar depois de reativar. Último login é atualizado nos próximos logins; não se fabrica histórico para contas anteriores.
- Exclusão definitiva exige conta desativada e texto `APAGAR <id>`. Conferem-se as chaves estrangeiras e CASCADE antes da exclusão. Arquivos são movidos temporariamente dentro de uploads; falha da transação restaura os arquivos. Após commit, os arquivos temporários são apagados. Uma interrupção do processo nessa última etapa pode exigir limpeza operacional dos arquivos `.admin-delete-*`; backups exigem política própria de retenção.
- Logs de auditoria contêm ação, IDs internos e detalhes técnicos restritos, sem credenciais, nomes, e-mails ou conteúdo dos documentos. IP aparece somente no histórico de tentativas. A retenção desses históricos precisa ser definida pelo responsável; não há promessa de limpeza automática dos logs.

## Migração sem perda de dados

`init_db()` usa `PRAGMA table_info` e `ALTER TABLE ADD COLUMN` apenas para colunas ausentes; cria somente tabelas/índices novos. Não usa DROP nem recria tabelas. A migração é idempotente.

`users`: `status`, `deactivated_at`, `last_login_at`, `session_version`. Contas existentes ficam ativas; datas de login anteriores ficam nulas.

O catálogo usado pelo site era JSON + `data/catalogo_sync.db`, não a antiga tabela `jobs`. O acervo original continua intacto. A tabela `courses` é criada e populada com o acervo atual. As duas tabelas recebem payload do formato atual, identidade por URL e flags de ocultação/remoção. Em `jobs`, a coluna preexistente `source` já representa o nome da fonte: ela é preservada, e `catalog_source` guarda `auto/manual`. Em `courses`, `source` guarda `auto/manual`, mantendo a instituição/fonte no payload.

O painel espelha as ofertas importadas ao listá-las, sem renovar datas. As decisões administrativas ficam no banco principal e são aplicadas a cada leitura pública, inclusive após uma importação real repetida. A URL original normalizada identifica os controles; uma oferta removida não pode ser reativada pela importação ou recadastrada na mesma URL. As automáticas só podem ser ocultadas, reexibidas ou removidas; edição é exclusiva das manuais. Links sem integração continuam separados dos anúncios, como antes.

Reexibir não confirma abertura nem prorroga validade. As contagens e a lista distinguem ofertas visíveis de ofertas fora da validade/validação. O cadastro manual exige área, resumo, evidência de abertura, prazo de revisão e requisitos; cursos também exigem evidência de acesso completo gratuito e condições do certificado. Preservou-se a exigência HTTPS e página individual do validador atual, mais restrita que aceitar HTTP. Não se coletam ofertas automaticamente ao preencher o formulário.

`sync_status(name,last_run_at,last_result,message)` fica no banco **do catálogo**, junto de `catalog_items` e `catalog_runs`, para o recibo ser transacional com o lote. `catalog_runs` continua a separar última tentativa de última verificação bem-sucedida por fonte. CLI registra sucesso/falha; entregas Jooble válidas registram o recebimento. Falha anterior à entrega no GitHub Actions só pode ser confirmada nos logs do Actions: não é inventada como uma tentativa recebida no servidor.

O agendamento existente não foi alterado nem verificado em produção nesta tarefa. A página Sistema apresenta execuções registradas; não garante que a rotina externa esteja ativa. A implementação não depende de Tasks pagas do PythonAnywhere.

## Aplicação no PythonAnywhere

Este trabalho não realizou commit, push, merge ou deploy. Primeiro revise e envie a branch de trabalho ao GitHub e integre-a à branch utilizada no servidor. Um `git pull` em `main` não traz alterações que continuam somente na branch local de trabalho.

1. No Console Bash, entre na pasta real do projeto (no exemplo existente):

```bash
cd ~/Projeto-Primeiro-Emprego-IA
git status
git branch --show-current
```

Se houver modificações locais ou arquivos não rastreados, preserve e compare antes de atualizar. Não use `reset --hard`, `clean` ou restauração geral para liberar o pull. Não reaplique automaticamente um stash antigo sobre a nova versão.

2. Ative o mesmo virtualenv configurado na aba Web e configure os mesmos caminhos usados no WSGI, caso já sejam personalizados. Faça backup ANTES de importar a nova aplicação ou executar a migração. O comando abaixo usa a API de backup do SQLite e arquiva uploads sem ler/imprimir conteúdo:

```bash
python - <<'PY'
import os, sqlite3, tarfile
from pathlib import Path
from datetime import datetime
root = Path.cwd()
backup = Path.home() / 'backups-primeiroemprego' / datetime.now().strftime('%Y%m%d-%H%M%S')
backup.mkdir(parents=True, mode=0o700)
paths = [
    ('principal.db', Path(os.environ.get('FIRST_JOB_DATABASE', root/'primeiro_emprego.db'))),
    ('admin.db', Path(os.environ.get('FIRST_JOB_ADMIN_DATABASE', root/'admin.db'))),
    ('catalogo.db', Path(os.environ.get('FIRST_JOB_CATALOG_DATABASE', root/'data/catalogo_sync.db'))),
]
for label, path in paths:
    if path.exists():
        with sqlite3.connect(path) as source, sqlite3.connect(backup/label) as target:
            source.backup(target)
uploads = Path(os.environ.get('FIRST_JOB_UPLOAD_DIR', root/'uploads'))
if uploads.exists():
    with tarfile.open(backup/'uploads.tar.gz', 'w:gz') as archive:
        archive.add(uploads, arcname='uploads')
print('Backup salvo em:', backup)
PY
```

Para um backup conjunto consistente, evite uploads, alterações e exclusões enquanto o backup estiver em andamento. Proteja e mantenha o backup fora das pastas servidas pelo site.

3. Com Git limpo e alterações já integradas à branch remota correta:

```bash
git pull --ff-only
python -m pip install -r requirements.txt
git ls-files '*.db' 'uploads/*'
```

O último comando deve listar somente `uploads/.gitkeep`. No checkout local isso foi conferido. Arquivos ignorados não são backup; preserve-os separadamente.

4. No arquivo WSGI da aba Web, ANTES de `from app import app as application`, configure:

```python
import os
os.environ['COOKIE_SECURE'] = '1'
os.environ['ADMIN_TRUST_PYTHONANYWHERE'] = '1'
# Opcional: caminhos absolutos para os bancos/pasta já utilizados pelo site.
# FIRST_JOB_DATABASE, FIRST_JOB_ADMIN_DATABASE, FIRST_JOB_CATALOG_DATABASE,
# FIRST_JOB_UPLOAD_DIR. Console e WSGI precisam apontar para os mesmos locais.
```

Mantenha a `SECRET_KEY` forte e persistente já usada pelo site, em configuração privada fora do Git. Se ainda não houver uma chave, gere e armazene fora do projeto, sem mostrá-la nos logs. Não substitua uma chave existente sem planejar o encerramento das sessões dos usuários. Preserve também `CATALOG_SYNC_TOKEN` e a configuração do catálogo; não copie chaves para README/JS/commits. Variáveis exportadas em um Console Bash não são automaticamente configuração do WSGI.

O cookie administrativo sempre é Secure; use o site por HTTPS. A confiança em `X-Real-IP` deve ser ativada somente no PythonAnywhere, cujo proxy sobrescreve esse cabeçalho. Não a ative em um servidor acessível diretamente pela internet.

5. No Console, com os mesmos caminhos e virtualenv:

```bash
python -c "from app import init_db; init_db(); print('Migração aditiva concluída.')"
python create_admin.py
```

O segundo comando pede usuário, senha e PIN sem exibir os segredos. Não os envie neste chat, não use argumentos e não grave o console em vídeo. Se já existir administrador, o script recusa substituí-lo; a troca normal é feita na seção Conta, com senha atual. Recuperação sem senha exige procedimento operacional no servidor, não há endpoint de recuperação.

6. Na aba Web, confira o WSGI/virtualenv e mapeamentos estáticos, clique **Reload**, e teste:

- Usuário comum continua entrando, editando perfil e acessando somente seus currículos.
- A chave sob o login abre PIN e depois usuário/senha; o painel não abre por URL sem autenticação.
- Desativação com uma conta descartável encerra sua sessão antiga.
- Ocultar/reexibir uma oferta não renova datas nem libera anúncios vencidos.
- Sistema mostra tentativa e sucesso separadamente. Confira a execução real do workflow antes de afirmar que a automação funciona.

Configuração WSGI: [guia oficial do PythonAnywhere para Flask](https://help.pythonanywhere.com/pages/Flask/). Proteções de cookies/CSRF: [guia oficial do Flask](https://flask.palletsprojects.com/en/stable/web-security/).

## Verificação e limites

Testes usam bancos, arquivos e credenciais aleatórias descartáveis. O roteiro de navegador grava evidências em `tmp/verificacao_admin/` (ignorado pelo Git). Não foi criada conta administrativa no banco real, nem apagado dado de produção.

Resultado em 16/11/2026: **83 testes Python passaram**, incluindo 19 novos testes administrativos; os dois testes existentes de JavaScript passaram; sintaxe dos dois novos scripts JavaScript passou; os seis módulos Python alterados/novos de produção passaram na verificação AST com sintaxe 3.10. Os fluxos reais em Chrome e a regressão de privacidade/cookies passaram, sem erros de JavaScript. `git diff --check` passou.

No navegador foram conferidos PIN e senha, teclado e foco dos modais, todas as seções, desativação/reativação, saída, inserção de HTML como texto, cadastro/edição/ocultação/reexibição/remoção de curso e telas de 1440px, 390px e visão geral de 320px. Imagens de desktop/celular foram inspecionadas. Os testes Python também cobrem PIN expirado, bloqueio persistido, token CSRF inválido/não ASCII, sessão inativa/revogada, IDs fora do limite do SQLite, exclusão com CASCADE e restauração de arquivos após falha da transação, importação repetida e URL editada sem retorno de item oculto.

Evidências locais: `tmp/verificacao_admin/python-suite.log`, `checks.json`, `resultado.json`, `visao-geral-desktop.png` e `usuarios-mobile.png`, além dos logs dos testes existentes. São arquivos ignorados, com fixtures, sem dados de produção. A regressão de privacidade grava suas evidências em `tmp/verificacao_legal/`.

O `git status` final identifica somente os 21 arquivos listados acima: nove modificados e doze novos. Não há banco, upload real, credencial ou dependência nova no diff.

Não houve execução em Python 3.10 real, leitor de tela, teste de carga, auditoria de invasão ou deploy. O código é compatível com sintaxe 3.10 e reaproveita dependências existentes, mas a configuração WSGI, HTTPS, permissões, espaço em disco, backups, retenção de logs e execução agendada precisam ser conferidas no servidor. Os logs administrativos não constituem trilha imutável contra quem já controla o servidor.
