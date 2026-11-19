# Catálogo do editor do site

Projeto: `C:\Users\felip\Documents\primeiro-emprego-ia`. O catálogo executável fica em `conteudo_editavel.py` e rejeita chaves desconhecidas.

| Página | Textos editáveis | Estrutura |
|---|---|---|
| Tela inicial/login | Chamada principal | Apresentação pode ser ocultada; login/cadastro são travados |
| Visão geral | Título, introdução e chamada do currículo | Introdução, atalhos e orientação podem ser ocultados/reordenados |
| Meu perfil | Título e introdução | Cabeçalho e campos profissionais travados; explicação do progresso pode ser ocultada |
| Vagas | Título e introdução | Cabeçalho e catálogo/filtros travados |
| Cursos | Título | Cabeçalho e catálogo/filtros travados |
| Meu currículo | Título e introdução | Cabeçalho, envio/criação e arquivos salvos travados |
| Minha conta | Título e introdução | Cabeçalho, segurança, formulários e privacidade travados |

Cada página tem um slot ao final para blocos de Texto, Aviso, Botão com link e Perguntas frequentes. São no máximo 30 blocos no site inteiro, com ordem e visibilidade próprias. Slots não se movem. Uma seção travada conserva sua posição original, inclusive nas requisições forjadas. Seções não travadas só podem trocar de posição dentro do mesmo grupo e sem deslocar as travadas.

Textos são simples (sem HTML e sem formatação Markdown nesta versão), até 120 caracteres nos títulos e 500 nas introduções. Quebras de linha são preservadas. Restaurar um texto recupera o padrão listado no catálogo.

Tema: primária (`--blue`), secundária (`--blue-deep`), fundo (`--cream`), texto (`--ink`) e destaque (`--orange`). Cores devem usar `#RRGGBB`. O tema só substitui as cores publicadas que diferem dos padrões; o visual original permanece como fallback. Contraste texto/fundo abaixo de 4,5:1 exige confirmação adicional na publicação.

Fontes: DM Sans e Plus Jakarta Sans, já distribuídas localmente com licença SIL OFL em `static/fonts/`. Títulos e corpo têm escolhas independentes. Logo PNG/JPEG/WEBP até 1 MB, validado e recodificado como PNG sem metadados, até 4 milhões de pixels; texto alternativo obrigatório até 160 caracteres.

Não são editáveis: Termos, Privacidade, Cookies, aceites, navegação, formulários, mensagens de validação, dados dinâmicos e o próprio painel. As prévias não consultam usuários, currículos ou ofertas reais; exibem apenas exemplos fixos identificados.

## Canvas por página e dispositivo

O catálogo de conteúdo acima permanece disponível no editor clássico. O catálogo de posicionamento fica em `canvas_login.py`. O servidor valida cada composição em computador e celular. A página pública usa o CSS original nos dispositivos sem composição publicada. Várias versões podem coexistir no histórico.

| Página | Elementos do canvas |
|---|---|
| Login | Título, ilustração e vidro opcional na coluna de apresentação |
| Visão geral | Chamada, título, introdução, botão de perfil, três atalhos e orientação |
| Meu perfil | Título, introdução, progresso, explicação e região de dados profissionais |
| Vagas e Cursos | Títulos de página, introdução/localização quando disponíveis e região de catálogo com filtros e resultados |
| Meu currículo | Título, introdução, situação da revisão, envio de PDF, chamada e botão de criação, currículos salvos |
| Minha conta | Título, introdução e botão Sair. Dados de acesso e formulários de segurança ficam fora da composição |

Cada página também aceita texto, card, botão com URL validada, aviso, perguntas frequentes, forma e cópia da ilustração local. Os blocos visíveis do catálogo anterior aparecem em Camadas. Uma edição de seu conteúdo no canvas cria uma versão específica daquele dispositivo. Regiões dinâmicas conservam os nós e eventos do site e permitem rolagem interna. A ordem do DOM acompanha a posição vertical e depois a horizontal, inclusive ao alternar de dispositivo.

**Escala e proteção.** O editor mede o layout original em uma janela de 1280 ou 390 px. A coluna do login no computador usa 560 unidades do piloto anterior. O quadro cresce com o conteúdo, tem margem inferior e largura máxima. Posições horizontais respeitam a largura da área. Formulários de login e cadastro, aceite, navegação, cookies e rodapé ficam fora da área de posicionamento e de sua pilha de camadas.

**Estilos e publicação.** A lista permitida inclui cores hexadecimais de seis ou oito dígitos, opacidades entre 0 e 1, desfoque de 0 a 40 px, raio de 0 a 48 px, borda de 0 a 12 px, quatro níveis de sombra, fonte de 12 a 96 px e três alinhamentos. O tema global continua usando cores de seis dígitos. Fontes explicitamente menores que 14 px bloqueiam a publicação no celular. A verificação de contraste estima a cor composta sobre o fundo escolhido. Imagens, transparências sobre outros elementos e a aparência final do vidro exigem inspeção visual.

**Persistência.** Rascunhos e publicações continuam nas tabelas existentes. As composições são opcionais no JSON de tema. A migração acrescenta `site_editor_meta` para a hora do salvamento. A auditoria do editor registra publicação, restauração, desfazer e troca de logo. A edição comum do rascunho não gera eventos com seu conteúdo. A folha pública passa por `/site-theme.css`, com ETag e política de estilos locais.

Consulte [Como usar](COMO_USAR.md) e o [roteiro de backup e atualização no PythonAnywhere](IMPLEMENTACAO.md).
