# Operação do catálogo — 13/11/2026

## Fluxo instalado

GitHub Actions consulta a API Jooble Brasil, filtra e valida o lote, envia por HTTPS para `/api/catalogo/sync` e exige recibo com a mesma data e quantidade. O Flask revalida e grava itens e recibo em uma única transação SQLite. O site lê `data/catalogo_sync.db` no próprio PythonAnywhere.

Conta: `PrimeiroEmpregoIA`. Projeto efetivamente importado pelo WSGI: `/home/PrimeiroEmpregoIA/Projeto-Primeiro-Emprego-IA`. Domínio: `https://PrimeiroEmpregoIA.pythonanywhere.com`.

O notebook pode ficar desligado. A rotina não depende de tarefas pagas no PythonAnywhere. O código não publica alterações futuras do site automaticamente: este workflow atualiza os dados do catálogo.

## Segredos

- `JOOBLE_API_KEY`: GitHub Actions Secrets; usada apenas na consulta ao Jooble.
- `CATALOG_SYNC_TOKEN`: GitHub Actions Secrets e `/home/PrimeiroEmpregoIA/.catalog-sync.json`, fora do repositório no servidor. O WSGI carrega essa configuração.
- O token da API PythonAnywhere foi usado para instalação e conferência. Não é necessário ao workflow e não foi enviado ao GitHub.

Nenhuma chave entra no código, relatório ou artefato do Actions. Para trocar o segredo de entrega, atualizar o arquivo privado e o secret homônimo, depois recarregar o webapp.

## Execução e observação

Workflow: `.github/workflows/catalogo.yml`, na branch `main`. Agenda diária: **06h17 de Brasília (09h17 UTC)**. O GitHub pode atrasar o disparo. Há também execução manual em Actions → Sincronizar catálogo → Run workflow → jobs.

O evento `schedule` foi comprovado em execuções concluídas com sucesso em 13/11/2026. Os horários temporários de teste foram removidos. A opção manual `courses` apenas diagnostica as fontes: não importa nem renova cursos.

O job instala dependências, executa testes isolados, diagnostica fontes e entrega vagas. `shell: bash` preserva a falha de comandos antes de `tee`. Relatórios JSON ficam no artefato `catalogo-<run_id>` por sete dias. Falhas deixam o Actions vermelho; dados anteriores permanecem, sujeitos à validade normal.

## Cobertura e limites

São três buscas, com até quatro páginas de cada: jovem aprendiz, estágio e sem experiência CLT, em Curitiba. A coleta para ao receber uma página vazia e faz no máximo 12 chamadas por rodada; a entrega limita-se a 100 registros únicos. A quota informada é 100 consultas/dia; execuções manuais também consomem quota. Não há paginação completa nem encerramento por ausência na amostra.

A resposta precisa conter localização Curitiba/PR, título adequado ao recorte, requisitos, área reconhecida e link individual com ID exato. Benefícios e o ramo da agência recrutadora não determinam a área. O título sozinho não comprova requisitos. Local e contrato confirmados também são enviados nos campos utilizados pelos cartões do frontend. IDs inteiros são preservados sem conversão para ponto flutuante. Ofertas sem evidência suficiente são descartadas, sem preencher lacunas com dados inventados.

Disponibilidade significa que a oferta foi retornada pela API naquela coleta; não garante que a empresa ainda aceite candidaturas. A data de revisão local vence no próximo ciclo. `expires_on` não é inventado. Conferir as condições completas no link da oferta.

O receptor exige segredo, cabeçalho da aplicação, corpo limitado e coleta nos últimos 15 minutos. Rejeita links fora do Jooble, entregas antigas e lotes inválidos. Repetir uma coleta já recebida não duplica registros. Banco de usuários, currículos e uploads não são substituídos.

## Cursos e fontes restantes

A Jooble fornece vagas. Cursos permanecem no catálogo existente e os portais oficiais continuam disponíveis; nenhuma rotina de importação de cursos foi ativada. A EV.G e seus três cursos foram removidos também da hospedagem, conforme solicitado. As demais fontes não receberam datas de verificação fictícias.

## Recuperação e testes

A cópia dos arquivos anteriores à instalação está em `tmp/deploy-backup-20261112/` no projeto local, ignorada pelo Git. Para reverter código, restaurar os arquivos correspondentes e o WSGI e recarregar o webapp. Não substituir bancos de usuários nem uploads. Para interromper somente a atualização, desabilitar o workflow no GitHub.

Testes locais: `.venv/Scripts/python.exe -m unittest discover -s tests -v`, com `FIRST_JOB_DATABASE`, `FIRST_JOB_UPLOAD_DIR` e `FIRST_JOB_CATALOG_DATABASE` apontando para temporários. Testes são sintéticos e separados da coleta real. A entrega real também foi conferida pelo recibo HTTP e pelo banco remoto.

## Evidências da instalação

- Entrega local inicial: 12/11/2026 às 17h35 de Brasília, uma vaga recebida no servidor.
- [Execução por push 43302465622](https://github.com/Felipe072008/Projeto-Primeiro-Emprego-IA/actions/runs/43302465622): testes, consulta e entrega concluídos com sucesso. Banco remoto confirmou `last_success_at=2026-11-12T17:39:51.060552-03:00` e `imported_count=1`.
- Registro recebido: Jovem Aprendiz em Informática, Quality Digital, Curitiba/PR, área Tecnologia, ID Jooble `-1632924386012570071`.
- Requisição ao receptor sem segredo retornou HTTP 401. Arquivos instalados foram relidos e comparados com a versão local.
- Nove cursos existentes foram preservados; três da EV.G foram retirados. Não houve importação automática de cursos.
- O site respondeu HTTP 200 após a recarga. A conferência visual da área autenticada depende de novo login pelo responsável, pois a configuração já existente gera uma chave de sessão diferente a cada reinício.

Conforme a [documentação do GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), execuções agendadas podem atrasar e repositórios públicos sem atividade por 60 dias têm seus agendamentos desativados automaticamente. Conferir a aba Actions periodicamente e reativar se necessário.
- [Diagnóstico manual de cursos 43304915658](https://github.com/Felipe072008/Projeto-Primeiro-Emprego-IA/actions/runs/43304915658): concluído com sucesso; etapa de coleta/entrega de vagas marcada `skipped`, como previsto.


## Ampliação e verificação em 13/11/2026

- [Execução automática 43470692728](https://github.com/Felipe072008/Projeto-Primeiro-Emprego-IA/actions/runs/43470692728) e execução automática 43346438857: evento `schedule`, ambas concluídas com sucesso.
- Causa da pouca cobertura inicial: consulta restrita à primeira página. A paginação agora alcança até quatro páginas por termo, mantendo os filtros de evidência e localização.
- 59 testes locais aprovados, incluindo limite de páginas, deduplicação e rejeição de requisitos/área inferidos do título ou da agência.
- Entrega real às 20h13 de Brasília: 14 registros recebidos com `sync_status=success`. Banco remoto: 21 registros publicados, dos quais 7 ainda válidos de coletas anteriores.
- Conferência visual na conta do responsável: 9 resultados no filtro do perfil de Tecnologia e 21 em Todas as áreas. Cartão conferido com fonte Jooble e verificação de 13/11/2026.
- A quantidade varia por coleta, prazo e filtro do perfil; 21 não é quantidade garantida para os dias seguintes. Cursos continuam sem importação automática.
