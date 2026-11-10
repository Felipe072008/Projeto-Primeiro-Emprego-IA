# Verificação da entrega

Executada em 2026-11-09T22:46:44.371549-03:00, no repositório `C:\Users\felip\Documents\primeiro-emprego-ia`.

- Projeto/caminho e abas visíveis confirmados no VS Code antes das edições.
- 49 testes Python passaram (32 anteriores e 17 novos). Fixtures não representam ofertas reais.
- Casos novos: importação do lote, repetição, fechamento completo, vazio confirmado, resposta parcial, formato/dados inválidos, falha de rede, manutenção HTML, ausência de integração autorizada, prazo de validade, filtros de custo/certificado, recorte de vagas, duplicatas com rastreamento, bloqueio de reaparecimento pelo acervo manual, concorrência, isolamento de fonte, calendário de Brasília e contrato das rotas.
- Página principal e recursos locais responderam HTTP 200 no cliente de teste Flask; não houve teste visual.
- CLI real `--source evg --probe`: erro `unexpected_format`; HTML de manutenção; nenhum curso importado e `last_success_at=null`.
- CLI `--due`: fontes não integradas ficaram bloqueadas; repetição devolveu `skipped` para todas, sem novas verificações.
- Exemplos JSON gerados das funções reais de resposta, sem dados pessoais; representam o acervo manual e os estados observados nesta execução.
- Nenhuma fonte real retornou um lote de ofertas importável. A documentação e os metadados de estágios não foram tratados como vagas.
- Nenhum adaptador de publicação real habilitado; nenhuma tarefa de agendamento instalada; nenhum deploy.
- `templates/pagina_principal.html` já estava modificado antes do trabalho (remoção de `div.noise`); essa alteração foi preservada. CSS e JavaScript não foram editados.

## Arquivos desta etapa

Alterados: `app.py` (parâmetro `certificate_free`), `catalogo_oportunidades.py` (validação compartilhada/contrato/leitura), `README.md` (guia).

Adicionados: `fontes_catalogo.py`, `sincronizacao_catalogo.py`, `data/fontes_catalogo.json`, `scripts/atualizar_catalogo.py`, `tests/test_sincronizacao_catalogo.py` e estes documentos/exemplos em `docs/catalogo/`.

Estado de execução local: `data/catalogo_sync.db`, ignorado pelo Git. Não contém perfis, currículos nem ofertas novas; somente as tentativas/bloqueios das fontes.

## Pendências reais

Obter o CSV válido da EV.G após a manutenção, confirmar esquema/completude e autorização aplicável ao arquivo, verificar condições por oferta e implementar/revisar seu adaptador. Para vagas, confirmar integração e licença ou atualizar o piloto municipal com ID/link individual e HTTPS válido. Confirmar hospedagem antes de instalar e verificar o agendador. A exibição dos novos campos, links externos, mensagens e validação mobile pertence à próxima etapa de Front End.
