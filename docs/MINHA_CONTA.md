# Minha conta — entrega de 17/11/2026

Projeto confirmado no VS Code: `C:\Users\felip\Documents\primeiro-emprego-ia`, branch `atualizar-primeiro-emprego-ia`.

## Arquivos completos no repositório

- `contas.py`: rotas autenticadas `/api/account/profile` (GET/PATCH), `/email`, `/password`, `/sessions`, `/export` e `/delete` (POST).
- `arquivos_conta.py`: exclusão de registros e arquivos compartilhada com o administrador; sem acesso a admin.db.
- `app.py`: registro das rotas e senha de 8 a 256 caracteres para novos cadastros.
- `admin.py`: reutilização da exclusão compartilhada, preservando a exigência de desativação para a exclusão administrativa.
- `static/interface_site.js`: integração da rota `account` e inicialização dos eventos.
- `static/minha_conta.js`: formulários, download e atualização imediata do nome/inicial.
- `static/minha_conta.css`: estilos responsivos, foco e alvo de toque do botão da conta.
- `templates/pagina_principal.html`: botão semântico único, inclusão da página e scripts; cadastro atualizado.
- `templates/parciais/minha_conta.html`: conteúdo de Dados da conta, Trocar senha, Segurança e Privacidade.
- `templates/politica_de_privacidade.html`: informa exportação e exclusão pela própria pessoa.
- `tests/test_contas.py`: testes novos das rotas, validação, bloqueio, sessões, exportação, exclusão e rollback.
- `tests/verificar_minha_conta.py`: teste completo no Chrome com conta e bancos descartáveis.
- `docs/MINHA_CONTA.md`: este roteiro.

As mudanças anteriores em `admin.py` e `tests/test_admin.py` para limite de GET/auditoria já estavam pendentes antes desta tarefa e foram preservadas. `tests/test_admin.py` não foi alterado nesta etapa. Não há alterações na página Meu perfil, barra lateral, banco administrativo, dependências ou configuração WSGI.

## Regras e suposições

- O bloco superior inteiro é um botão com `data-route=account`, foco visível, Enter/Espaço e rótulo “Abrir Minha conta”. Sem novo item lateral.
- E-mail exige senha atual e confirmação, é salvo em minúsculas e verifica duplicação inclusive contra endereços antigos com maiúsculas. Não há envio de mensagem nem confirmação de propriedade da caixa.
- A senha nova tem 8–256 caracteres, confirmação e deve diferir da atual. Senhas antigas menores continuam válidas no login. Troca de senha incrementa `session_version` e atualiza apenas esta sessão; sair de todos encerra também a atual.
- O nome muda apenas em `users`, sem reescrever os currículos já gerados nem dados profissionais. Alterar e-mail não encerra sessões; a revogação permanece nas ações de senha/sessões.
- Tentativas erradas são compartilhadas entre e-mail, senha, exportação e exclusão. Contadores por usuário e IP ficam em `request_limits`, com prefixo `account:`; a janela começa no primeiro erro, e o quinto inicia bloqueio de 15 minutos. Erros persistem mesmo quando a alteração é recusada. Sucessos não apagam falhas recentes. Os registros vencidos são removidos na próxima tentativa protegida. Contas diferentes no mesmo IP compartilham o bloqueio por IP.
- Reutiliza a configuração de confiança do PythonAnywhere já existente, `ADMIN_TRUST_PYTHONANYWHERE`, sem importar ou consultar admin.db. Se ela não estiver ativada, usa o endereço da conexão e ignora cabeçalhos encaminhados. Em proxy não configurado, isso pode compartilhar o limite entre visitantes; mantenha a configuração já documentada para o ambiente.
- O ZIP contém `dados.json` e somente os arquivos pertencentes à conta, sob nomes seguros `arquivos/curriculo-ID.pdf`. O JSON inclui dados da conta, perfil, seções, aceites, metadados e conteúdo dos currículos gerados. Nunca inclui hashes, versão de sessão, tokens, caminhos internos ou dados de outra conta. Arquivos ausentes são sinalizados no JSON. O ZIP é criado sob demanda em armazenamento temporário e não é salvo no projeto.
- A exportação mantém uma transação durante a leitura dos arquivos para evitar corrida com exclusão/troca de credenciais; grandes acervos podem demorar e ocupar espaço temporário. Não foi realizado teste de carga.
- Exclusão própria exige senha e `EXCLUIR`; não exige desativação prévia. A exclusão administrativa continua exigindo desativação. Ambas verificam CASCADE e usam o mesmo procedimento de movimentação temporária, rollback/restauração e limpeza após commit. Falha na limpeza após commit é informada; interrupção abrupta nessa fase pode deixar `.admin-delete-*` para limpeza operacional. Backups não são apagados automaticamente.
- Nenhuma migração nova, serviço pago ou dependência foi necessária. As rotas de conta não acessam admin.db; o teste impede esse acesso explicitamente.

## Testes

Suíte Python completa: 94 testes aprovados em Python 3.14. Regressões JavaScript/Chrome aprovadas, executadas com bancos temporários. git diff --check sem erros. Testes novos cobrem entradas inválidas, e-mail duplicado, senhas antigas, revogação de sessões, limite por usuário/IP, expiração, exportação isolada, ausência de hashes, CASCADE e restauração de arquivo após falha da transação. A regressão administrativa também verifica a exclusão compartilhada.

Chrome real: botão superior via Espaço, nome/inicial, e-mail, senha e botão Mostrar, janela existente de cookies, download do ZIP, saída de todos, novo login e exclusão definitiva. Layout conferido em desktop e larguras 390/320px, sem transbordamento. Evidências em `tmp/verificacao_conta/`, ignorado pelo Git. Credenciais e registros usados são exclusivamente fixtures descartáveis.

Python disponível: 3.14. Sintaxe dos novos módulos verificada como Python 3.10; execução real em 3.10 não foi realizada porque o interpretador não está instalado. Não houve deploy ou validação de produção/leitor de tela.

## Aplicar no PythonAnywhere

1. Revise, faça commit e envie as mudanças para a branch utilizada pelo servidor. Se o servidor usa `main`, integre primeiro a branch de trabalho. Confirme `git status` e preserve quaisquer alterações locais antes do pull.
2. Faça backup do banco principal **antes** de atualizar, com o virtualenv e caminho de banco já usados pelo site:

```bash
cd ~/Projeto-Primeiro-Emprego-IA
python - <<'PY'
import os, sqlite3
from pathlib import Path
from datetime import datetime
source_path = Path(os.environ.get('FIRST_JOB_DATABASE', 'primeiro_emprego.db')).resolve()
backup_dir = Path.home() / 'backups-primeiroemprego'
backup_dir.mkdir(exist_ok=True, mode=0o700)
backup_path = backup_dir / ('conta-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.db')
with sqlite3.connect(source_path.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(backup_path) as target:
    source.backup(target)
print('Backup:', backup_path)
PY
```

Preserve também os uploads pelo procedimento de backup existente, especialmente antes de testar exclusões. Não use contas reais como teste descartável.

3. Com a branch correta e árvore limpa, execute `git pull --ff-only` e clique em **Web → Reload**. Não é necessário criar contas, instalar dependências novas ou alterar o WSGI.
4. Entre com uma conta de teste e confira o botão Minha conta, troca de nome, download e retorno ao login ao sair de todos. Exclusão é definitiva; use somente uma conta descartável para validá-la.
