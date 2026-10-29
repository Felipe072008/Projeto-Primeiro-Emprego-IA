# Implementação da auditoria — 28/10/2026

## Local e segurança dos dados

Trabalho realizado em uma **cópia isolada** em `C:\Users\felip\Documents\ChatGPT\Site`, a partir dos fontes de `C:\Users\felip\Documents\primeiro-emprego-ia`. A pasta inicialmente aberta na sessão estava vazia. Não copiamos banco, uploads, ambiente virtual nem histórico Git. O repositório original e o site publicado não foram alterados.

Stack confirmada: Flask, SQLite, JavaScript sem framework, ReportLab e pypdf. Nenhuma dependência nova, API paga ou instalação de modelo. Testes de interface usaram somente a conta fictícia `auditoria@example.test`, banco e uploads em `tmp/`.

## Resultado por achado

| Auditoria | Alteração / decisão |
|---|---|
| 1–2 / A | Confirmado nos arquivos: os 16 anúncios antigos foram consultados em 08/10 e tinham revisão até 22/10. Permanecem ocultos. Adicionado um anúncio de estágio em infraestrutura em Curitiba, verificado em 28/10, com revisão em 04/11. A API informa disponibilidade do catálogo; a tela distingue ausência de catálogo, filtro sem correspondência e erro, oferece limpar filtros e buscas externas identificadas como buscas. Cobertura explicitamente restrita a Curitiba/PR; não foi criado seletor de cidades sem cobertura. |
| 3 / D | Botão “Revisar estrutura” e carregamento coerentes quando a consulta ao serviço de IA não indica disponibilidade. Sem texto de instalação no fluxo. Falhas do modelo continuam retornando revisão automática identificada. Ausência de vagas compatíveis tem explicação explícita. Nenhuma IA foi instalada. |
| 4 / B | Validação compartilhada no servidor para PUT antigo, PATCH de contato e progresso. Cliente valida DDD, fixo de 10 dígitos ou celular de 11 iniciado por 9; zeros e formatos inválidos são rejeitados. Idade 1–120 preserva a regra já existente, não é regra de elegibilidade. Campo numérico tem mínimo/máximo; valores negativos não são transformados silenciosamente em positivos. Dados antigos não são apagados e aparecem como pendências de revisão. |
| 5–6 / E | “Perfil básico completo”, “Revisar perfil”, critérios expostos, botão geral “Editar dados pessoais”, explicação de nome/e-mail bloqueados. Experiência não exigida para completar o básico. Não criamos alteração de e-mail sem verificação de identidade. |
| 7 / F | Separados área/setor, cargo-alvo, vínculo e modalidade. Leitura compatível infere área e vínculos das opções anteriores sem escrever no banco. O cargo-alvo alimenta o currículo. Áreas adicionais agora sugerem áreas sem prefixos de contrato. Rótulos antigos e seus mapeamentos permanecem nos fontes para compatibilidade. |
| 8 / F–G | Ao adicionar formação, o texto anterior aparece como referência para transcrição assistida. Instituição, situação e demais dados devem ser confirmados pelo titular. Nenhuma formação é inventada; o texto antigo só é removido explicitamente. Currículos mostram que são versões independentes. |
| 9 / G | Nome na criação, renomeação em formulário, data com hora e identificador. Editar cria nova versão; duplicar preserva conteúdo anterior. A edição oferece caminho separado para criar a partir do perfil. Prévia, análise e PDF usam o mesmo `content_json`. Vazio omitido. Guardas de rascunho no criador e na edição de versões. |
| 10–11 / H | Instituição/fonte iguais não são repetidas. Cursos de áreas genericamente correlatas ficam em exploração. Suporte de TI prioriza fundamentos de hardware, sistemas e redes; termos explícitos de habilidades/objetivo também justificam recomendações. Incluído curso certificado de fundamentos de TI. Sem promessa de curso técnico inexistente. |
| 12 / J | Singular/plural de resultados, texto de curso no estado vazio, aviso de obrigatoriedade condicional, menos repetição de “Meu perfil”. |
| 13 / C | Marco `main` autenticado, link de pular conteúdo, `aria-current`, menu recolhido com `inert`/`aria-hidden`, ciclo de foco do menu e retorno ao acionador. Modais mantêm contenção e retorno, incluindo quando a lista de currículos foi renderizada novamente. Alvos principais de 44 px e respeito a movimento reduzido. |
| 14 / I | Hashes por seção, voltar/avançar e abertura direta. Filtros em `sessionStorage` na aba, sem termos ou dados pessoais na URL. Botão limpar filtros. Erros preservam campos e filtros; controles de submissão desabilitados durante envio. |
| 15 / J | Chamada de cursos mais compacta no celular, notas e erros legíveis e redução de rótulos repetidos. Identidade visual preservada. |
| 16 / D | Revisão explica limites de regras e de redação; não promete ortografia completa. A frase positiva de objetivo já era limitada a expressões monitoradas e foi mantida. Reescritas contextualizadas permanecem sugestões, sem alterar fatos automaticamente. |

## Fontes conferidas nesta execução

- Vaga: [Bellinati Perez — Estagiário de T.I / Infraestrutura](https://bellinatiperez.gupy.io/jobs/12467350). Página pública com candidatura, Curitiba/PR, 6h diárias, curso técnico ou graduação em TI, Windows e Office. Não foi realizada candidatura. Salário não informado foi mantido como tal.
- Curso: [Fundamentos de TI: Hardware e Software — Escola Virtual](https://www.ev.org.br/cursos/fundamentos-de-ti-hardware-e-software). 7h, iniciante, idade mínima 14 anos, prazo 60 dias; página e termos descrevem gratuidade e certificado para aprovados.
- Telefone: [Anatel — perguntas sobre numeração](https://www.gov.br/anatel/pt-br/regulado/numeracao/perguntas-frequentes) e [nono dígito](https://www.gov.br/anatel/pt-br/regulado/numeracao/codigos-nacionais/nono-digito). A validação é de formato, não confirma existência ou titularidade da linha.

Não foram revalidados todos os anúncios/cursos antigos, nem testadas candidaturas e matrículas. O catálogo não é um coletor automático de vagas. `scripts/review_catalog.py` continua listando registros vencidos ou próximos da revisão; só atualize `checked_on`/`review_by` após abrir e conferir a fonte individual.

## Verificação técnica

**27 testes Python passaram**, além das verificações de sintaxe dos dois arquivos JS e dos testes sintéticos de frontend. Logs em `testes-python.txt` e `testes-frontend.txt`.

Cobertura automatizada: cadastro/login/logout, autenticação inválida, isolamento de duas contas, autorização por dono em leitura/arquivo/PDF/análise/edição por nova versão/renomeação/exclusão, gravação independente de seções, legados preservados, datas e trabalho atual, duplicatas, áreas adicionais, progresso, filtros, vencimento do catálogo, versões independentes, PDF longo com acentos e limites de upload.

PDFs de teste: válido, conteúdo não PDF com extensão PDF, vazio, corrompido, protegido, digitalizado sem texto, acima de 8 MB, excesso de páginas e nome inseguro. O teste propositalmente corrompido emite `EOF marker not found`. A execução também registrou `ResourceWarning` de arquivo temporário do teste multipart; não foi ocultado e não é falha de asserção.

Proteção contra requisições cruzadas: cabeçalho obrigatório `X-Requested-With: FirstJob` nas mutações, rejeição de `Origin` diferente e ausência de CORS liberado. Cookies HttpOnly/SameSite=Lax e Secure configurável. Limitação em SQLite: 30 tentativas de autenticação e 10 análises por janela de 15 minutos, com HTTP 429. O endereço vem de `remote_addr`, sem confiar cegamente em `X-Forwarded-For`. Validar o endereço real percebido pelo WSGI na hospedagem antes de publicar, para evitar um limite compartilhado pelo proxy.

**Recuperação de senha não existe nesta base**: não havia fluxo para exercer, nem infraestrutura de envio verificada. Não foi inventado envio de e-mail ou política de recuperação. A alteração segura de credenciais continua dependendo de uma decisão de produto e configuração futura.

## Interface exercitada

- Login fictício; salvar contato e pretensões; idade 999 rejeitada nativamente; telefone só zeros recusado com erro junto ao campo e rascunho mantido.
- Vaga e curso verificados exibidos, curso técnico sem resultado com mensagem específica; filtro restaurado após recarga.
- Criação, prévia, edição em nova versão, duplicação, renomeação e revisão automática de currículo. Originais preservados.
- Histórico voltar/avançar entre Vagas e Cursos; `aria-current` acompanhando seção.
- Menu mobile com Escape e retorno de foco; modal de contato com Tab/Shift+Tab, contenção e retorno após Escape.
- Medidas de **5 seções × 5 larguras: 360, 390, 768, 1024 e 1440 px**, um `main` visível e sem rolagem horizontal nas medições. `responsivo.json` guarda os resultados. Modal de contato nas mesmas larguras em `modais.json`.
- Cinco pares de cores da paleta medidos por luminância: 15,75; 5,56; 5,40; 7,58 e 4,84. Todos acima de 4,5:1. Ver `contraste.json`. Isso não é uma certificação de conformidade WCAG da página inteira ou de todos os estados.
- Consulta de console da aba de teste não retornou erros/avisos capturados. Não equivale a monitoramento completo.

Capturas reais da área visível: `curriculos.jpg`, `versoes-mobile.jpg` e `pretensoes-desktop.jpg`. Captura de página inteira falhou tanto no Chrome quanto no navegador integrado; um teste de captura com viewport maior apresentou área preta da ferramenta e foi descartado. Capturas da área visível funcionaram depois, incluindo o editor de pretensões em desktop. A interrupção após diálogo nativo de renomeação foi da automação; o fluxo final de renomeação em modal foi testado em outra aba.

Pendências de verificação: leitor de tela, outros motores como Firefox/Safari, rede realmente limitada, download manual em disco e implantação real no PythonAnywhere. PDFs e downloads autenticados foram verificados pela API. Não houve medição de desempenho sob carga nem execução de modelo de IA real.

## Arquivos e compatibilidade

Alterados: `app.py`, `catalog.py`, `profile_data.py`, `resume_analysis.py`, `static/app.js`, `static/profile.js`, `static/redesign.css`, `static/occupations.json`, `templates/index.html`, `data/jobs.json`, `data/courses.json`, `tests/test_app.py`, `tests/test_profile_sections.py`, `tests/check_frontend.cjs`, `README.md`.

Novo: `tests/test_audit.py` e esta pasta de evidências. Os arquivos de teste e os catálogos continuam com dados fictícios/públicos; nenhum banco de produção acompanha a entrega.

Migração: `init_db()` cria apenas a tabela adicional `request_limits` se ausente. Novos campos `sector` e `target_role` residem no JSON de seções existente. Não há remoção de coluna/tabela, nem conversão destrutiva de texto livre. Títulos usam `resumes.original_name`, já existente. Versões usam novas linhas na tabela existente. APIs novas: `PATCH /api/resumes/<id>` e `POST /api/resumes/<id>/version`.

Clientes de API externos precisam enviar `X-Requested-With: FirstJob` nas mutações. A interface desta entrega já o faz. Não configure CORS irrestrito, pois a proteção contra CSRF depende do impedimento de cabeçalhos personalizados entre origens.

## Executar localmente

Na pasta desta cópia:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Abra `http://127.0.0.1:5000`. A conta e o banco padrão começam vazios nesta cópia. Não distribua `tmp/`, `.venv/`, `.env`, bancos ou uploads junto aos fontes.

Testes:

```powershell
New-Item -ItemType Directory -Force tmp
$env:TEMP=(Resolve-Path tmp).Path
$env:TMP=$env:TEMP
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/app.js
node --check static/profile.js
node tests/check_frontend.cjs
```

Na execução desta auditoria foi reutilizado o Python do ambiente virtual do projeto original; isso não copia nem modifica esse ambiente.

## Implantação futura, sem publicação nesta entrega

1. Compare a cópia com a versão efetivamente publicada, inclusive eventuais mudanças recentes no servidor. Faça commit/backup dos fontes anteriores.
2. Antes de reiniciar a aplicação com código novo, faça backup consistente do SQLite e dos uploads. Com aplicação parada, copie ambos; com aplicação ativa, use a API de backup do SQLite, evitando cópia bruta durante escrita.
3. Atualize fontes preservando banco, uploads, segredo e configuração. Nunca substitua o banco real por um banco de teste. O pacote só contém arquivos alterados e evidências.
4. Configure `SECRET_KEY` estável, `FIRST_JOB_DATABASE` e `FIRST_JOB_UPLOAD_DIR` apontando aos dados reais. Em HTTPS, use `COOKIE_SECURE=1`. Não use `app.run(debug=True)` na hospedagem: use WSGI e recarregue o aplicativo pelo painel do provedor.
5. Confira limites do plano e o esquema/host recebido pelo Flask; teste login, validação de origem, salvamento e download em conta de teste. Faça atualização completa do navegador para usar o JS novo com o cabeçalho de segurança.
6. Revise os catálogos novamente se a implantação ocorrer depois das datas de validade. Não instale Ollama nesta hospedagem sem verificar suporte e recursos. Sem serviço, a revisão de estrutura funciona.

## Reversão

Pare/recarregue a aplicação e restaure os fontes anteriores. `request_limits` pode permanecer, sem afetar a versão anterior. Guarde uma cópia do banco posterior à implantação antes de qualquer restauração. Não restaure o banco antigo automaticamente: isso perderia perfis e currículos criados depois do backup. Campos JSON novos e versões novas devem ser preservados. Se houver incompatibilidade confirmada, faça migração dirigida em cópia, conferindo registros antes de trocar os dados em produção.
