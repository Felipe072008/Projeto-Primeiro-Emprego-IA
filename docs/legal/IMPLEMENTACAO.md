# Termos, privacidade e cookies — implementação de 13/11/2026

## Destino e escopo

Projeto confirmado no VS Code: `C:\Users\felip\Documents\primeiro-emprego-ia`; `app.py` ativo. O Git começou limpo. Esta etapa integra as páginas, os componentes da interface e o backend no projeto atual, sem recriar o site. Não houve push, publicação ou deploy. Nenhuma mensagem/e-mail foi enviada.

O responsável foi informado pelo usuário como **Felipe Correia de Oliveira**. O e-mail foi corrigido pelo usuário para **primeiro.emprego.ia@gmail.com**; o domínio `.com.br` do anexo não foi usado. A recepção de mensagens da caixa não foi testada.

## Funcionamento

- Rotas públicas: `/termos-de-uso`, `/politica-de-privacidade` e `/cookies`; não exigem sessão.
- Datas documentais fixas em `documentos_legais.py`: revisão e versões `2026-11-13`. O ano do rodapé é calculado no servidor a cada renderização; não altera as datas das políticas.
- Rodapé compartilhado e links funcionais no cadastro, com documentos em nova aba para preservar o formulário.
- Cadastro requer `terms_accepted: true` (booleano) e `terms_version: "2026-11-13"`. Valores ausentes/falsos ou versão antiga retornam HTTP 400 antes de criar a conta.
- A tabela `terms_acceptances` guarda somente `user_id`, `terms_version` e `accepted_at`. O aceite e a conta são gravados na mesma transação. Não coleta IP para esse registro.
- `CREATE TABLE IF NOT EXISTS` acrescenta a tabela ao iniciar o Flask. Contas e arquivos existentes são preservados; nenhum aceite é atribuído retroativamente. Login de contas antigas continua disponível.
- O banner mostra três escolhas equivalentes: Aceitar Todos, Rejeitar Opcionais e Gerenciar Preferências. Continuar navegando não grava consentimento.
- A interface lê o estado validado de preferências antes de ler/gravar filtros opcionais. Rejeição não impede autenticação nem busca.
- O painel usa diálogo nativo, contém o foco por teclado, fecha com Escape e devolve o foco ao acionador. O tratamento de teclado não fecha modais do aplicativo por trás dele.

## Inventário efetivo

| Recurso | Categoria | Finalidade e duração |
|---|---|---|
| Cookie Flask `session` | Necessário | Sessão autenticada; cookie de sessão sem prazo persistente definido pelo app; removido no logout. HttpOnly e SameSite=Lax; Secure depende de `COOKIE_SECURE=1` na hospedagem HTTPS. |
| localStorage `primeiroemprego.cookie_preferences` | Necessário para respeitar a escolha | Versão, categorias e instantes de gravação/expiração, sem nome/e-mail. Validade de 180 dias; registro inválido, expirado ou de outra versão é descartado em novo acesso. localStorage não tem limpeza automática por prazo pelo navegador. |
| sessionStorage `filters-jobs`, `filters-courses` | Funcionalidade opcional | Lembrar filtros na aba, somente após escolha específica ou Aceitar Todos. Revogar elimina os dois registros. A busca continua funcionando sem armazenamento. |
| Google Analytics / pixels / publicidade | Não utilizados | Não foram adicionados rastreadores, scripts fictícios nem consentimentos para ferramentas inexistentes. Controles aparecem desativados e identificados como não utilizados. |
| DM Sans / Plus Jakarta Sans | Recurso visual local | Arquivos oficiais foram trazidos para `static/fonts/` com as licenças SIL Open Font License. Nenhuma consulta a Google Fonts na navegação das páginas. |

As preferências são locais ao navegador, sem vínculo com a conta e sem criação de um banco de rastreamento. A recarga preserva uma decisão válida. A revogação é propagada às outras abas da mesma origem por evento de storage. Se o navegador bloquear gravação, a página informa que a escolha vale só naquela página e que o banner pode reaparecer. As categorias de análise e marketing permanecem falsas; Aceitar Todos autoriza apenas a categoria funcional existente.

Se novos fornecedores/scripts opcionais forem adicionados no futuro, deverão ser inventariados, ter carregamento condicionado à categoria, interrupção/remoção na revogação e política/versão revisadas. Não basta inserir uma tag externa no HTML e confiar neste gerenciador.

## Tratamentos conferidos no código

- Nome/e-mail/hash de senha, perfil estruturado e textos anteriores em SQLite.
- PDFs em uploads com nomes internos, conteúdo validado e acesso por proprietário; exclusão de currículo remove registro e arquivo ativo.
- Currículos gerados e suas versões armazenados no banco; PDF produzido no servidor.
- Orientações por regras e análise contextual opcional por Ollama em loopback. O código aceita somente endereço local; não há API OpenAI para currículos.
- Consulta Jooble usa termos genéricos e Curitiba; não envia perfil, e-mail ou PDF dos usuários.
- Limitação de tentativas usa identificadores derivados e janelas de 15 minutos; não é Analytics.
- Não existe envio automático de currículos a recrutadores, sistema de alertas por e-mail, venda de dados ou publicidade implementada.
- Não existe exclusão automática de conta por inatividade nem interface de exclusão de conta.

## Verificação

- 64 testes Python passaram, incluindo 5 novos testes de páginas públicas, data fixa, validação do aceite, transação e migração de usuários anteriores.
- Verificações JavaScript existentes de interface e catálogo passaram.
- Teste real `tests/verificar_privacidade.py`, com Chrome headless e banco/arquivos temporários, passou pelos 12 cenários solicitados. Relatório em `testes-navegador.json`.
- Viewports de desktop 1440x1000, celular 390x844 e largura mínima 320px; cinco telas do aplicativo, gerador de currículo e três rotas legais verificadas sem rolagem horizontal. Capturas inspecionadas em `tmp/verificacao_legal/`.
- Nenhum erro JavaScript nas páginas testadas; nenhuma requisição a serviço de rastreamento/terceiro. As fontes foram carregadas da própria origem.
- Testes usam perfis sintéticos e nunca aceitam Termos em nome do usuário real. Não houve inspeção de configurações/contratos/logs da hospedagem nem teste com leitor de tela real.

Para repetir os testes de navegador, disponibilize Playwright no Python de testes e execute `python tests/verificar_privacidade.py`. O Chrome instalado é usado via `channel=chrome`. Playwright foi instalado somente na pasta temporária de ferramentas deste trabalho, não em `requirements.txt`. Os testes Python regulares continuam usando `python -m unittest discover -s tests -v`.

## Confirmações antes de publicação definitiva

1. Revisão jurídica dos textos e das bases legais efetivas por atividade, especialmente dados de crianças/adolescentes. O perfil atual admite idade de 1 a 120 para validação numérica, mas isso não comprova consentimento ou elegibilidade; não há fluxo de responsável legal.
2. Definir e documentar retenção/exclusão de contas, logs, aceites e backups; formalizar o atendimento aos direitos dos titulares. Não foram inventados prazos de retenção ou procedimento já operacional.
3. Confirmar contrato, localização de processamento e suboperadores da hospedagem PythonAnywhere e eventuais transferências internacionais. Não foi presumida hospedagem integral no Brasil.
4. Validar recepção do e-mail corrigido e processo de resposta às solicitações, sem envio de mensagens por este trabalho.
5. Conferir HTTPS, `COOKIE_SECURE=1`, chave de sessão, permissões de arquivos e backups no ambiente real. O texto descreve medidas presentes no código sem prometer segurança absoluta.
6. Em mudanças futuras relevantes nos Termos, definir comunicação e reaceite quando aplicável. Nesta entrega, o registro é exigido para novos cadastros; contas antigas não foram bloqueadas nem receberam aceite inventado.

Essas pendências também são expostas na política em revisão. As páginas e o banner não equivalem a certificação de adequação integral à LGPD.

## Referências consultadas

- [Guia da ANPD sobre cookies](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_cookies_e_protecao_de_dados_pessoais).
- [Recomendações da ANPD para consentimento granular e rejeição de opcionais](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-emite-recomendacoes-para-adequacao-da-pratica-de-coleta-de-cookies-do-portal-gov.br).
- [Fontes oficiais e licenças Google Fonts](https://github.com/google/fonts).

## Arquivos

Novos: `documentos_legais.py`, `templates/base_legal.html`, `templates/termos_de_uso.html`, `templates/politica_de_privacidade.html`, `templates/politica_cookies.html`, `templates/parciais/rodape.html`, `templates/parciais/cookies.html`, `static/preferencias_cookies.js`, `static/privacidade.css`, `static/fontes_locais.css`, arquivos/fontes/licenças em `static/fonts/`, `tests/test_documentos_legais.py`, `tests/verificar_privacidade.py` e estes documentos de entrega.

Modificados: `app.py`, `templates/pagina_principal.html`, `static/interface_site.js`, os cadastros sintéticos em `tests/test_aplicacao.py`, `tests/test_secoes_perfil.py`, `tests/test_seguranca_regressoes.py`, `tests/verificar_catalogo_real.cjs` e a simulação de preferência funcional em `tests/verificar_catalogo_frontend.cjs`; README atualizado com instruções.
