# Atualização manual e agendamento

## Estado atual

Não há adaptador externo habilitado nem agendamento instalado. Nenhuma oferta nova foi importada. Esta entrega prepara o armazenamento, validação, transação, estados e ponto de entrada da rotina; não resolve os bloqueios de dados/licença documentados em [FONTES.md](FONTES.md).

O usuário informou a conta PythonAnywhere `felipecorreia` e confirmou a aba Tasks vazia. O painel não pôde ser inspecionado diretamente nesta sessão; nenhuma execução agendada foi comprovada. Não foi feito deploy. Nenhuma tarefa foi criada no Windows: os passos abaixo são para instalação futura. Um agendamento no notebook depende de ele estar ligado e disponível. Nada garante execução com o computador desligado.

## Comandos no repositório

```powershell
Set-Location C:\Users\felip\Documents\primeiro-emprego-ia
.\.venv\Scripts\python.exe scripts\atualizar_catalogo.py --source evg --probe
.\.venv\Scripts\python.exe scripts\atualizar_catalogo.py --kind jobs
.\.venv\Scripts\python.exe scripts\atualizar_catalogo.py --kind courses
.\.venv\Scripts\python.exe scripts\atualizar_catalogo.py --due
```

`--probe` consulta apenas o CSV público conhecido da EV.G, com timeout, limite de tamanho, TLS normal e sem seguir redirecionamentos. HTML/manutenção não é CSV. Mesmo que receba CSV, não publica sem validar o esquema e as condições por oferta: retorna `schema_pending`. Não interpreta nomes de colunas hipotéticos como dados reais.

Sem `--due`, força uma tentativa (teste/recuperação). Com `--due`, tenta no máximo uma vez por ciclo em Brasília, contando tentativas falhas/bloqueadas; para recuperar antes do próximo ciclo, execute sem essa opção. `--source` seleciona uma fonte. A execução com fontes bloqueadas retorna código **1**, com motivo em JSON; sucesso ou ciclos já tentados retornam **0**. Falhas internas de armazenamento resultam em erro do comando, sem simular sucesso.

Cadência sugerida: vagas **diariamente às 06h**, cursos **segunda-feira às 06h30**, em `America/Sao_Paulo`. O comando calcula o último ciclo vencido nessa zona, independente do fuso do sistema. Não inicia uma tarefa por requisição, por worker Flask nem pelo reloader.

## Como agendar quando o ambiente estiver definido

Windows: no Agendador de Tarefas, criar tarefa que rode a cada hora com:

- Programa: `C:\Users\felip\Documents\primeiro-emprego-ia\.venv\Scripts\python.exe`
- Argumentos: `"C:\Users\felip\Documents\primeiro-emprego-ia\scripts\atualizar_catalogo.py" --due`
- Iniciar em: `C:\Users\felip\Documents\primeiro-emprego-ia`
- Não iniciar uma nova instância enquanto a anterior executa; executar quando possível após horário perdido.

Em servidor Linux com cron, ajustar os caminhos reais e instalar, **somente depois de confirmar a hospedagem**, uma entrada equivalente a:

```cron
0 * * * * cd /caminho/primeiro-emprego-ia && .venv/bin/python scripts/atualizar_catalogo.py --due >> /caminho/logs/catalogo.log 2>&1
```

O cron dispara a consulta horária; o Python decide se o ciclo de Brasília venceu. Verificar uma execução real e o resultado persistido antes de anunciar automação ativa. Manter um único armazenamento persistente compartilhado entre aplicação e rotina; ambientes efêmeros/múltiplas máquinas exigem escolha de armazenamento antes da instalação. Isso não está configurado nesta entrega.

## Persistência e recuperação

Banco separado: `data/catalogo_sync.db` (ignorado pelo Git por `*.db`). Sobrescreva o caminho com `FIRST_JOB_CATALOG_DATABASE`; aplicação e comando devem usar o mesmo caminho absoluto. Não usa tabelas de usuários, currículos nem uploads. O catálogo manual permanece em `data/jobs.json` e `data/courses.json` sem atualizar datas.

Um lote completo passa pela validação comum do catálogo e pelas validações de evidência do motor. A chave `(source_id, source_item_id)` torna a repetição idempotente. A leitura também elimina links equivalentes com parâmetros de rastreamento. A escrita de itens e o sucesso da fonte são atômicos. Um lock SQLite serializa execuções concorrentes; falha na transação faz rollback.

Resposta parcial, formato alterado, duplicatas internas, requisitos ausentes ou falha de rede preservam integralmente o último lote válido e `last_success_at`. Só uma lista completa com contagem consistente encerra itens por ausência. Lista vazia exige confirmação explícita do adaptador (`empty_confirmed=true`). A confirmação de completude não é um parâmetro controlado pela interface pública.

O motor exige `review_by` explícito e limita a revisão a um ciclo (1 dia para vagas, 7 para cursos). Esse prazo é política de revisão local, não prazo de inscrição. `expires_on` só vem da fonte. O término da validade continua ocultando itens mesmo durante falhas. Um encerramento por ausência conserva a última verificação da oferta e registra `closed_at` separadamente.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para isolamento completo inclusive durante o import de `app.py`, aponte `FIRST_JOB_DATABASE`, `FIRST_JOB_UPLOAD_DIR` e `FIRST_JOB_CATALOG_DATABASE` para diretórios temporários antes de executar. Os testes novos usam fixtures sintéticas e não fazem rede. Cobrem lote inicial, repetição, fechamento, lista vazia, erro/parcial, expiração, filtros e estados das rotas. A existência de fixtures aprovadas não autoriza nenhuma fonte externa.

Não executar o script de geração de áreas durante a importação: ele não é um atualizador de ofertas.

## GitHub Actions — diagnóstico preparado em 10/11/2026

O workflow `.github/workflows/catalogo.yml` executa os testes do backend em Python 3.13 e uma consulta diagnóstica. Dispara quando o próprio workflow é enviado ao GitHub e permite execução manual após chegar à branch padrão (`main`). Na execução manual, selecione vagas ou cursos; para cursos, a opção EV.G testa a exportação oficial.

O resultado JSON fica no artefato `diagnostico-catalogo-<run_id>`, retido por sete dias, inclusive quando a fonte falha. A falha produz execução vermelha, sem transformar uma tentativa em sincronização bem-sucedida. Bancos e uploads de testes usam diretórios temporários.

A conta de destino confirmada pelo usuário é `PrimeiroEmpregoIA`. O WSGI visualizado aponta para `/home/PrimeiroEmpregoIA/Projeto-Primeiro-Emprego-IA`, e o domínio é `PrimeiroEmpregoIA.pythonanywhere.com`. O campo Source code do painel mostra outro caminho (`mysite`); conferir os arquivos efetivos antes de qualquer entrega.

Esta etapa não transfere dados para a hospedagem. O registro de adaptadores está vazio e a exportação EV.G respondeu HTTP 200 com HTML da aplicação JavaScript. O agendamento diário/semanal depende de uma importação real autorizada e de entrega transacional validada. A criação de credencial e seu armazenamento em GitHub Secrets foram autorizados pelo usuário, mas ainda precisam ser executados.

Execução comprovada em 10/11/2026: https://github.com/Felipe072008/Projeto-Primeiro-Emprego-IA/actions/runs/42908028381 . Os 52 testes passaram no executor Linux com Python 3.13. A etapa de consulta EV.G terminou com código 1; o artefato de diagnóstico foi publicado. Isso comprova a execução no GitHub, mas não uma importação ou atualização do site. A primeira versão do workflow foi rejeitada por contexto indisponível no ambiente do job; corrigida antes desta execução.
