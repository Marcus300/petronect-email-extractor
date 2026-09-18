# Histórico de versões

Este projeto segue tags no formato `vMAJOR.MINOR.PATCH.REVISION`. As versões publicadas permanecem disponíveis no histórico de releases do GitHub.

## [0.0.2.1] — 2026-09-17

### Adicionado

- Tela de carregamento inicial na própria janela, com identidade visual do projeto, anel circular em `Canvas`, progresso determinado por etapas e animação indeterminada durante a conexão com o Outlook.
- Log de inicialização com tempos decorridos em `%LOCALAPPDATA%\PetronectEmailExtractor\logs`, incluindo conexão COM, quantidades de caixas e pastas, aplicação dos dados, erros e tempo até a interface pronta.
- Testes automatizados do agendamento pós-renderização, worker COM, fila de dados simples, progresso monotônico, animação indeterminada, recuperação de falha e importação tardia do exportador Excel.
- Parser dedicado para e-mails de Pedido de Compra do SAP Business Network / Ariba.
- Extração do Pedido `45XXXXXXXX`, Contrato `46XXXXXXXX`, Cliente, Status dinâmico, Versão, Valor Total e Moeda.
- Validação cruzada do número do pedido entre Subject e bloco `Pedido de compra`, mantendo o Subject como fonte principal e registrando divergências.
- Fallbacks delimitados e auditáveis para Pedido, Contrato, Cliente, Valor Total e Moeda, sem capturar números ou valores genéricos do Body.
- Layout Excel exclusivo de `Pedido` com dez colunas, autofiltro, cabeçalho congelado e formatação própria.
- Testes com pedidos novos e alterados, USD e BRL, múltiplos valores, status dinâmico, clientes compostos, contratos repetidos ou divergentes e campos ausentes.

### Alterado

- O reinício após atualização agora define `PYINSTALLER_RESET_ENVIRONMENT=1` antes de abrir o novo executável e repete a substituição enquanto o arquivo anterior estiver temporariamente bloqueado, evitando falhas ao carregar `python314.dll` de uma pasta `_MEI` já removida.
- A carga inicial de caixas e pastas do Outlook deixa de bloquear o construtor e passa a ocorrer em uma thread daemon agendada pelo Tkinter após a primeira renderização, com toda atualização gráfica processada na thread principal por `Queue`.
- Uma única fonte Outlook é reutilizada no worker inicial; COM é inicializado e finalizado dentro dessa mesma thread, sem transportar objetos COM para a interface.
- A geração de Excel passa a ser importada somente quando uma extração é iniciada, reduzindo trabalho anterior à primeira renderização.
- O calendário passa a manter uma única instância por janela principal; cliques repetidos restauram, trazem para frente e focalizam o popup existente, e o fechamento pelo botão ou pelo `X` limpa sua referência com segurança.
- Os dias do calendário passam a usar uma paleta local de alto contraste, com estados visualmente distintos para data normal, hoje, data selecionada e hoje selecionado, sem modificar o tema global da aplicação.
- Pedidos alterados com mais de um conjunto `Valor + Moeda` passam a utilizar o último par completo anterior a `Versão:`.
- Pedido e Contrato são exportados como texto; Valor Total é exportado como decimal real com formatação monetária, sem depender do locale.
- `Data e hora de recebimento`, `Assunto` e `ID` preservam respectivamente `ReceivedTime`, Subject e a origem já consolidada no pipeline.
- Os layouts e parsers de `Sala`, `Prorrogada` e `Cancelada` permanecem isolados do novo fluxo de Pedido.

## [0.0.2.0] — 2026-09-17

### Adicionado

- Parser dedicado para notificações `Prorrogada`, acionado exclusivamente pelo `Subject`.
- Tipo determinístico `Prorrogação de Oportunidade` para todos os registros da categoria.
- Extração exclusiva do trecho `Nova data final: “DD.MM.AAAA, HH:MM:SS” (Horário de Brasília)`.
- Prioridade para o conteúdo posterior a `ZjQcmQRYFpfptBannerEnd`, evitando preheader e banner de segurança.
- Fallback no Body completo quando o marcador não existe, com seleção da última ocorrência válida em caso de valores diferentes.
- Avisos de auditoria para fallback, datas finais divergentes e falha de parsing sem descarte do registro.
- Testes de variações do Subject, datas e horários, preheader, banner, fallback, conteúdo descartado e ausência de mensagem válida.
- Comparação programática da estrutura dos arquivos Excel de `Sala` e `Prorrogada`.
- Calendário determinístico em PT-BR, com semana iniciando em domingo, botão `Hoje` e estados visuais distintos para hoje, data selecionada e hoje selecionado.
- Download automático do executável oficial da última release, com arquivo parcial, validação de origem, nome, tamanho e estrutura PE antes da instalação.
- Processo auxiliar no Windows para aguardar o encerramento, substituir o executável e reiniciar a aplicação sem corromper o arquivo em uso.
- Registro do SHA-256 calculado após o download da atualização.
- Parser dedicado para notificações `Cancelada`, classificadas por qualquer Subject que contenha esse texto sem diferenciar capitalização.
- Tipo fixo `Oportunidade Cancelada` e extração da mensagem a partir de `foi cancelada pelo seguinte motivo:`.
- Preservação de motivos normais, curtos, multilinha, vazios e com valor literal `0`.
- Prioridade para o motivo posterior ao banner de segurança e fallback auditável para o Body completo quando o marcador não existir.
- Bloqueio da execução antes da criação do log ou acesso ao Outlook quando a data e hora de corte estiverem no futuro.
- Opção `0.Conjunto (Sala, Prorrogação, Cancelamento)` na lista de assuntos, preservando integralmente o texto entre parênteses.
- Pesquisa conjunta com correspondência alternativa para `sala`, `prorrogada` ou `cancelada` durante uma única varredura do Outlook.

### Alterado

- O filtro `Prorrogada` passa a localizar qualquer Subject que contenha esse texto, ignorando maiúsculas e minúsculas.
- `Sala` e `Prorrogada` compartilham a mesma rotina e o mesmo layout estruturado de Excel, sem duplicação da exportação.
- Os demais filtros preservam o layout genérico com `Body` original.
- A lista de pastas do Outlook é recarregada ao abrir o campo `Pasta e subpastas`, preservando a seleção atual e exibindo subpastas sincronizadas após a abertura da aplicação.
- O cabeçalho do calendário passa a acompanhar imediatamente a navegação entre meses e anos, sem depender do idioma configurado no Windows.
- O botão e o título `About` passam a ser exibidos como `Sobre`.
- Dropdowns de caixas, subpastas irmãs e assuntos passam a ser ordenados alfabeticamente, sem alterar a hierarquia lógica das pastas.
- O botão `Atualizar` deixa de abrir a página de Releases e passa a baixar, validar e preparar diretamente o asset oficial publicado no GitHub.
- `Cancelada` passa a reutilizar exatamente o mesmo schema e layout de Excel de `Sala` e `Prorrogada`.
- Testes de regressão passam a cobrir conjuntamente os parsers e layouts de `Sala`, `Prorrogada` e `Cancelada`.
- No filtro conjunto, cada e-mail passa pelo parser determinado pelo próprio Subject e é gravado diretamente no mesmo Excel estruturado, sem pesquisas separadas ou mesclagem posterior.

## [0.0.1.2] — 2026-09-17

### Adicionado

- Fallback seguro que consulta o link oficial `releases/latest` e obtém a versão pelo redirecionamento do GitHub.
- Uso da pilha HTTPS e dos certificados confiáveis do Windows no fallback de atualização.
- Log técnico independente em `%LOCALAPPDATA%\PetronectEmailExtractor\logs` quando todas as consultas de atualização falham.
- Campo de assunto com lista suspensa editável de tipos de notificação.
- Layout genérico de Excel com a coluna `Body` contendo o corpo original e sem tratamento.
- Diagnóstico por pasta com intervalo mínimo e máximo de recebimento, quantidade dentro do período, itens não-email, classes MAPI e tipos de data retornados pelo Outlook.
- Amostras estruturais e anônimas de até três mensagens por pasta, contendo apenas tipos, datas normalizadas, comprimentos, quantidade de anexos e tamanho em bytes.
- Registro de fuso horário, deslocamento UTC, codificação regional e estratégia de normalização da data.
- Preenchimento automático do destino com `emails_petronect.xlsx` na pasta Downloads do usuário atual, localizada pela API de pastas conhecidas do Windows.
- Lista de assuntos com as opções `Sala`, `Nova Oportunidade`, `Chamado`, `Cancelada`, `Prorrogada`, `Pedido` e `Relatório`.
- Mapeamento interno de cada opção para um ou mais termos de assunto, com correspondência alternativa quando houver vários termos.
- Restrição da pesquisa aos remetentes `ordersender-prod@ansmtp.ariba.com` e `petronect@petronect.com.br`.
- Documentação da arquitetura planejada para conexão futura ao Microsoft Graph e dos requisitos de Microsoft Entra ID.

### Alterado

- Falhas da consulta de atualização agora exibem uma orientação curta na interface, mantendo exceções e detalhes técnicos no arquivo de log.
- A API pública do GitHub permanece como consulta principal; o link direto é usado automaticamente quando a API não pode ser validada ou acessada.
- O assunto passa a ser opcional e continua aceitando texto livre além dos itens da lista.
- O tratamento em `Tipo` e `Mensagem` fica restrito ao filtro `Sala`; filtros diferentes ou vazios utilizam o layout genérico.
- A conversão prioriza componentes numéricos de objetos COM; datas textuais inequívocas são detectadas e datas ambíguas respeitam explicitamente a localidade do Windows.
- O resumo informa quando nenhum e-mail atingiu a data inicial e esclarece quando o filtro de assunto não chegou a ser aplicado.
- Logs de datas inválidas deixaram de registrar o texto do assunto e passaram a informar somente seu comprimento.
- O seletor de destino passa a abrir com a pasta e o nome atualmente informados, mantendo a possibilidade de alterá-los livremente.
- A opção `SALA` passa a ser exibida como `Sala`; termos usados na pesquisa permanecem ocultos na lista.
- As duas definições solicitadas para `Chamado` foram consolidadas em uma opção única que pesquisa `Atenção ao Chamado`, `ticket` ou `chamado`.
- O README passa a priorizar a instalação e o uso do executável e deixa de apresentar uma seção específica de testes.

## [0.0.1.1] — 2026-09-16

### Adicionado

- Consulta automática da última release ao abrir a aplicação.
- Janela própria, com o ícone do projeto, para notificar uma versão mais recente.
- Ações “Atualizar” e “Fechar” na notificação de nova versão.
- Exibição da última versão publicada na janela About.

### Alterado

- O botão do About agora é “Atualizar” e permanece desabilitado quando não existe versão superior.
- O calendário e as janelas auxiliares passam a utilizar o ícone padrão do projeto.
- A atualização abre diretamente a página oficial da release disponível.
- As mensagens de quantidade foram padronizadas para `email(s)` e `exportado(s)`.
- O README passa a registrar o roadmap das próximas funcionalidades.

## [0.0.1.0] — 2026-09-16

### Adicionado

- Interface gráfica para seleção da caixa de correio, pasta e subpastas do Outlook.
- Pesquisa recursiva de mensagens pelo Outlook desktop clássico via COM.
- Filtros por data, hora inicial e trecho do assunto.
- Edição direta dos segmentos de dia, mês, ano, hora e minuto.
- Calendário auxiliar para seleção visual da data.
- Extração de IDs Petronect no padrão `700` seguido de sete dígitos.
- Interpretação de notificações Petronect com separação de tipo e mensagem.
- Compatibilidade com notificações que contêm anexos e diferentes formatos de corpo.
- Exportação para Excel com data de recebimento, assunto, ID, tipo e mensagem.
- Formatação de cabeçalho, filtros, larguras, quebra de texto e congelamento da primeira linha no Excel.
- Gravação atômica da planilha para evitar arquivos finais incompletos.
- Seleção livre do local e nome do arquivo de saída.
- Abertura do arquivo Excel mais recente pela interface.
- Cancelamento controlado da pesquisa em andamento.
- Log visual durante a execução.
- Log técnico em arquivo com ambiente, plataforma, arquitetura, caminhos e critérios utilizados.
- Contagem por pasta de mensagens analisadas, datas inválidas, mensagens anteriores ao período e assuntos não correspondentes.
- Registro de traceback completo em falhas da extração.
- Log de emergência para erros ocorridos antes da abertura da interface.
- Inicialização COM independente na interface e na thread de processamento.
- Listagem de pastas de entrada em instalações do Outlook em diferentes idiomas suportados.
- Janela About com identidade visual, licença MIT e contatos do mantenedor.
- Ícone e logo incorporados ao executável.
- Build portátil para Windows 64 bits com PyInstaller.
- Versionamento centralizado do aplicativo e metadados de versão do Windows.
- Validação automática da correspondência entre versão, metadados e tag Git.
- Testes automatizados para limpeza, interpretação Petronect, Outlook, exportação, interface, diagnóstico e atualização.
- Workflow de integração contínua para validar pushes e pull requests no Windows.
- Workflow de release para testar, gerar e anexar o executável a uma GitHub Release.
- Geração automática e categorizada das notas de release.
- Links no README para a release mais recente e para o histórico completo.
- Verificação automática e manual da última release pela API pública do GitHub.
- Documentação de instalação, uso, segurança, contribuição, estrutura e código de conduta.

[0.0.1.0]: https://github.com/marcus300/petronect-email-extractor/releases/tag/v0.0.1.0
[0.0.1.1]: https://github.com/marcus300/petronect-email-extractor/releases/tag/v0.0.1.1
[0.0.1.2]: https://github.com/marcus300/petronect-email-extractor/releases/tag/v0.0.1.2
[0.0.2.0]: https://github.com/marcus300/petronect-email-extractor/releases/tag/v0.0.2.0
[0.0.2.1]: https://github.com/marcus300/petronect-email-extractor/releases/tag/v0.0.2.1
