# Conferência do documento de auditoria — 28/10/2026

Documento de referência: `C:\Users\felip\Downloads\auditoria_primeiroemprego_ia.md`.
Projeto de destino confirmado pelo status do VS Code: `C:\Users\felip\Documents\primeiro-emprego-ia`.

Esta conferência compara os 16 achados e as entregas A–J com o código, os testes e as evidências disponíveis. O relatório inicial `RELATORIO.md` descreve a implementação em cópia isolada; esta conferência registra a revisão adicional e a aplicação local autorizada posteriormente. Não houve publicação na hospedagem.

## O que foi alterado e o que permanece parcial

| Item | Situação | Resultado e limite |
|---|---|---|
| 1 / A — Vagas | Parcial | A causa de catálogo vazio foi identificada: as 16 vagas antigas venceram a revisão em 22/10. Continuam ocultas. Há um anúncio adicional de estágio em infraestrutura com consulta registrada em 28/10 e revisão até 04/11. Não existe cobertura de vagas ativas para todas as áreas, nem coleta automática diária. O script de manutenção já existente lista revisões pendentes. |
| 2 / A — Estados vazios e filtros | Implementado | Carregamento, falha, catálogo sem revisão válida e busca sem correspondência têm mensagens diferentes. Limpar filtros funciona. “Todas as áreas” não é sugerido quando já selecionado. Não há seletor de localização porque o catálogo de vagas cobre somente Curitiba/PR; a interface informa isso. |
| 3 / D — Capacidade de IA | Implementado para a capacidade disponível | Consulta ao serviço local, botão e carregamento coerentes com revisão de estrutura. Fallback explícito. Não foi instalado modelo, conforme orientação anterior do proprietário. A presença do modelo no serviço não garante que toda geração concluirá; falhas têm fallback. |
| 4 / B — Telefone e idade | Implementado | Validação de DDD, fixo/celular, comprimento e sequências inválidas no cliente e servidor. Idade 1–120 mantém a regra anterior, sem definir elegibilidade. Mensagens próximas dos campos e rascunho preservado. Dados antigos ficam visíveis como pendência e deixam de contar como válidos no progresso. |
| 5 / E — Conclusão do perfil | Implementado | “Perfil básico completo” e “Revisar perfil”, critérios visíveis, sem exigir experiência profissional. |
| 6 / E — Botão e dados da conta | Implementado com limite explícito | Botão “Editar dados pessoais”; nome/e-mail bloqueados com explicação. Não foi criado fluxo de alteração de e-mail/nome nem verificação de identidade. |
| 7 / F — Área e vínculos | Implementado | Área, cargo-alvo opcional, contratos e modalidade separados. Escolhas antigas interpretadas de forma compatível, sem sobrescrever o banco ao ler. Áreas adicionais continuam disponíveis. Modalidade é informativa, não é filtro de vagas. |
| 8 / F–G — Formação antiga e origem | Parcial | Texto antigo aparece como referência para transcrição assistida; usuário confirma instituição, datas e situação. Texto livre preservado. Currículo mostra origem e independência do perfil. Não há conversão automática de texto livre, nem origem histórica detalhada que não existia nos registros antigos. |
| 9 / G — Versões de currículo | Implementado | Nomear, renomear, horário/ID, editar em nova versão, duplicar e criar outra a partir do perfil. Original preservado. Prévia, revisão e PDF usam o conteúdo salvo da versão. |
| 10 / H — Instituição duplicada | Implementado | Fonte igual à instituição não se repete; fonte diferente é identificada. |
| 11 / H — Recomendações de cursos | Parcial | Cargo, habilidades e objetivo com termos explícitos; suporte de TI prioriza hardware/sistemas/redes. Cursos apenas genericamente correlatos ficam em exploração. Adicionado curso de fundamentos de TI. Não há cursos técnicos cadastrados nem correspondência semântica completa para todos os cargos. |
| 12 / J — Textos | Implementado | Singular/plural, mensagens próprias de cursos, aviso de obrigatoriedade condicional e menos rótulos repetidos no perfil. |
| 13 / C — Acessibilidade | Implementado no código; validação parcial | Marco principal autenticado, pular conteúdo, `aria-current`, menu recolhido com `inert`/`aria-hidden`, foco e Escape. Evidências anteriores de teclado, modais e medidas de contraste estão anexadas. Sem certificação WCAG, leitor de tela ou todos os estados medidos. |
| 14 / I — URL e histórico | Implementado | Hash por seção, voltar/avançar e recarga; filtros preservados por aba em `sessionStorage`, sem dados pessoais na URL. Não há histórico independente de cada alteração de filtro. |
| 15 / J — Mobile e densidade | Implementado; validação visual parcial | Chamada de cursos menor, controles legíveis, alvos principais de 44 px, contraste e movimento reduzido. Medições anteriores em 360/390/768/1024/1440 px disponíveis; nem todos os textos e alvos da página foram certificados. |
| 16 / D — Redação | Parcial | Limites da revisão automática explícitos; comparação com vagas ausentes é identificada; sugestões do modelo, quando disponível, permanecem revisáveis. Não existe corretor ortográfico completo. Não houve execução de modelo real. |

## Problemas adicionais corrigidos nesta revisão

- Idade com dígitos Unicode como `²` causava erro 500 no PATCH de contato. Reproduzido por teste; removida conversão redundante e aplicada a validação central de dígitos ASCII.
- Ano de conclusão com caracteres semelhantes a números e URL de certificado como `https://[` também causavam erro 500. Reproduzidos por testes; agora retornam 400 com erros de campo e preservam o perfil anterior.
- Seções de uma nova versão aceitam apenas os campos de conteúdo previstos; campos adicionais enviados são descartados antes da persistência.
- Modal de renomeação/versão não fecha durante o envio; criar a partir do perfil fica bloqueado enquanto a versão é salva.
- Análise de currículo gerado com mais de 20 páginas retorna mensagem útil (422), em vez de erro não tratado. Geração/download permanecem separados do limite de análise.
- Rolagem após salvar perfil respeita a preferência de movimento reduzido também quando acionada pelo JavaScript.

## Verificação e limites atuais

A suíte contém 28 testes Python, incluindo persistência independente, duas contas, autorização de currículos, upload PDF, limites, dados legados, catálogo, versões e os novos casos de validação. Sintaxe de `static/app.js` e `static/profile.js` e verificações sintéticas de frontend também são executadas. Os logs da execução no projeto de destino acompanham esta conferência.

Os testes usam banco e uploads temporários; a aplicação não é importada com os caminhos de dados reais. Um backup dos fontes anteriores é criado antes da aplicação. Banco e uploads reais são comparados por hash antes/depois, sem copiar conteúdo pessoal para a entrega.

Nesta rodada, a ferramenta de controle visual encerrou o acesso ao Chrome por não conseguir determinar a URL com confiança. Não foram feitas novas afirmações de validação visual. As capturas e medições existentes pertencem à etapa anterior e não comprovam os pequenos ajustes posteriores.

Links de todos os 12 cursos retornaram as respectivas páginas de curso na consulta web desta revisão. Isso não confirma matrícula, certificado individual ou todas as condições atuais; as datas do catálogo não foram estendidas só pela resposta dos links. O anúncio Gupy adicional não pôde ser reaberto pela ferramenta web nesta rodada: sua consulta anterior está registrada no relatório inicial; não foi declarado removido nem revalidado. Não foram exercitadas candidaturas ou matrículas externas.

Pendentes: recuperação de senha (não existe infraestrutura de e-mail definida), edição segura de credenciais, revisão ortográfica completa, modelo local operacional, maior cobertura de vagas, cursos técnicos, Firefox/Safari, leitor de tela, rede limitada real, desempenho sob carga e verificação na hospedagem. A rotina não altera a conta real nem publica o site.

## Migração e reversão

A tabela `request_limits` é aditiva. Os campos novos do perfil usam JSON existente; títulos e versões usam a tabela de currículos existente. Não são removidos registros ou colunas. Na próxima inicialização local, a tabela adicional será criada automaticamente.

Para reverter, pare o servidor e restaure somente os fontes do backup. Preserve banco e uploads atuais. O backup de fontes não contém bancos, uploads, `.env`, ambiente virtual ou histórico Git. Veja as instruções de hospedagem e reversão de dados em `RELATORIO.md` antes de uma implantação futura.

## Aplicação local confirmada

Arquivos aplicados diretamente em `C:\Users\felip\Documents\primeiro-emprego-ia`, a pasta aberta no VS Code. Os 28 testes Python, as duas verificações de sintaxe JavaScript, os testes sintéticos de frontend e `git diff --check` passaram nessa pasta. Banco, uploads e configuração protegida existentes mantiveram os mesmos hashes. Backup dos fontes anteriores: `C:\Users\felip\Documents\ChatGPT\Site\backup-fontes-antes-revisao-2026-10-28.zip`. Nenhum commit, push ou deploy foi realizado.
