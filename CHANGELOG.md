# Histórico de versões

Este projeto segue tags no formato `vMAJOR.MINOR.PATCH.REVISION`. Esta é a primeira versão de distribuição pública; não existem releases públicas anteriores.

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
