<h1 align="center">
  <img src="docs/logo/logo.png" alt="Petronect Email Extractor" width="120" height="120">
</h1>

<div align="center">
  <strong>Petronect Email Extractor</strong><br>
  <sub>Pesquisa notificações Petronect no Outlook e gera um Excel estruturado.</sub><br><br>
  <a href="#sobre"><strong>Conheça o projeto »</strong></a>
</div>

<div align="center">
  <br>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/versão-0.0.1.2-blue" alt="Versão 0.0.1.2">
  <img src="https://img.shields.io/badge/status-estável-brightgreen" alt="Status estável">
  <img src="https://img.shields.io/badge/licença-MIT-yellow" alt="Licença MIT">
  <a href="https://github.com/marcus300/petronect-email-extractor/releases/latest"><img src="https://img.shields.io/badge/release-latest-2ea44f" alt="Última release"></a>
</div>

<details open>
<summary><strong>Índice</strong></summary>

- [Sobre](#sobre)
  - [Tecnologias](#tecnologias)
  - [Estrutura do projeto](#estrutura-do-projeto)
- [Primeiros passos](#primeiros-passos)
  - [Pré-requisitos](#pré-requisitos)
  - [Instalação](#instalação)
  - [Atualizações pelo GitHub](#atualizações-pelo-github)
  - [Conexão Microsoft Graph](#conexão-microsoft-graph)
- [Como usar](#como-usar)
- [Funcionalidades](#funcionalidades)
- [Logs e diagnóstico de datas](#logs-e-diagnóstico-de-datas)
- [Última release](#última-release)
- [Roadmap](#roadmap)
- [Releases e versões anteriores](#releases-e-versões-anteriores)
- [Segurança](#segurança)
- [Código de conduta](#código-de-conduta)
- [Contribuição](#contribuição)
- [Contato](#contato)

</details>

<hr>

<h2 id="sobre">Sobre</h2>

O Petronect Email Extractor automatiza a leitura de notificações no Outlook, filtra mensagens por data, hora e assunto, extrai os dados relevantes e gera uma planilha Excel acompanhada de um log técnico detalhado.

> **Ponto de entrada:** [`main.py`](main.py)

<h3 id="tecnologias">Tecnologias</h3>

- **Python 3.10+**, testado com Python 3.14.2.
- **Tkinter** para a interface gráfica.
- **pywin32** para integração COM com o Outlook desktop clássico.
- **Microsoft Graph** previsto como fonte futura para consultar o Exchange Online sem depender do cache do Outlook clássico.
- **openpyxl** para geração segura das planilhas Excel.
- **PyInstaller** para geração do executável Windows.

<h3 id="estrutura-do-projeto">Estrutura do projeto</h3>

Consulte [`docs/STRUCTURE.md`](docs/STRUCTURE.md) para mais detalhes.

```text
sala/
├── docs/                       # Documentação e identidade visual
├── email_extractor/            # Código principal da aplicação
├── tests/                      # Testes automatizados
├── build_exe.ps1               # Build do executável
├── main.py                     # Ponto de entrada
├── requirements.txt            # Dependências de execução
└── version_info.txt            # Metadados da versão Windows
```

<h2 id="primeiros-passos">Primeiros passos</h2>

<h3 id="pré-requisitos">Pré-requisitos</h3>

- Windows 64 bits.
- Outlook desktop clássico instalado e com perfil configurado.
- Permissão de acesso às caixas de correio pesquisadas.
- Python 3.10 ou superior somente para executar pelo código-fonte.

> O novo Outlook para Windows não disponibiliza a automação COM exigida pelo projeto.

<h3 id="instalação">Instalação</h3>

Para utilizar o executável no Windows:

1. Acesse a [página da release mais recente](https://github.com/Marcus300/petronect-email-extractor/releases/latest).
2. Baixe o arquivo `Petronect.Email.Extractor.vX.X.X.X.exe`.
3. Salve ou mova o executável para uma pasta local comum, como Documentos ou uma pasta de aplicativos.
4. Não execute o programa diretamente de dentro de um arquivo `.zip`; extraia-o primeiro, se necessário.
5. Abra e sincronize o **Outlook (clássico)** com a caixa compartilhada que será pesquisada.
6. Execute o arquivo `.exe`. Não é necessário instalar Python para usar a versão distribuída.

Se o Windows SmartScreen exibir um aviso para um executável ainda não assinado digitalmente, confirme que o arquivo veio da página oficial da release e compare seu hash quando ele estiver publicado nas notas da versão.

Para executar pelo código-fonte ou contribuir com o projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

<h3 id="atualizações-pelo-github">Atualizações pelo GitHub</h3>

A aplicação consulta em segundo plano a API pública de `marcus300/petronect-email-extractor/releases/latest`. Se a API falhar, tenta automaticamente o link oficial `releases/latest` por meio da pilha HTTPS do Windows e extrai o número da versão do redirecionamento para a tag publicada. Esse fallback respeita os certificados confiáveis, o proxy e as políticas de segurança configuradas no Windows; a validação SSL nunca é desabilitada.

Quando uma versão numericamente superior estiver disponível, o usuário poderá abrir sua página de download. A consulta também pode ser iniciada manualmente no About e não exige token ou credenciais. Se os dois métodos falharem, a interface apresenta uma orientação curta e grava os detalhes técnicos em `%LOCALAPPDATA%\PetronectEmailExtractor\logs`.

<h3 id="conexão-microsoft-graph">Conexão Microsoft Graph</h3>

A versão 0.0.1.2 ainda consulta mensagens pelo Outlook clássico via COM. O novo Outlook não disponibiliza essa automação para aplicativos externos. Está planejada uma segunda fonte baseada no Microsoft Graph, que consultará a caixa diretamente no Exchange Online e não dependerá de qual Outlook está aberto nem do cache local.

<h2 id="como-usar">Como usar</h2>

Uso recomendado do executável:

1. Abra o **Outlook (clássico)** e aguarde a sincronização da caixa compartilhada. Os e-mails exibidos apenas no novo Outlook ainda não podem ser lidos pela versão atual.
2. Abra `Petronect Email Extractor v0.0.1.2.exe` fora de qualquer arquivo compactado.
3. Selecione a caixa de pesquisa e a pasta do Outlook.
4. Informe a data e a hora inicial digitando os campos ou utilizando o calendário.
5. No assunto, selecione uma opção da lista, digite um texto livre ou deixe o campo vazio.
6. Confirme o destino sugerido `Downloads\emails_petronect.xlsx` ou use **Escolher** para alterar a pasta e o nome.
7. Clique em **Pesquisar e gerar Excel** e acompanhe o log.
8. Ao finalizar, utilize **Abrir Excel recente** para abrir o arquivo gerado.

As opções de assunto disponíveis são:

- `Sala`
- `Nova Oportunidade`
- `Chamado`
- `Cancelada`
- `Prorrogada`
- `Pedido`
- `Relatório`

Os termos internos utilizados por cada opção não são exibidos na lista. Opções com mais de um termo aceitam qualquer um deles. Independentemente do assunto escolhido, somente mensagens enviadas por `ordersender-prod@ansmtp.ariba.com` ou `petronect@petronect.com.br` são consideradas.

Ao abrir a aplicação, o campo **Salvar Excel em** é preenchido automaticamente com `emails_petronect.xlsx` na pasta Downloads do usuário que executou o programa. A pasta é localizada pelas pastas conhecidas do Windows, inclusive quando Downloads estiver redirecionada. O botão **Escolher** continua permitindo alterar livremente o diretório e o nome do arquivo.

<h2 id="funcionalidades">Funcionalidades</h2>

- Seleciona caixas, pastas e subpastas do Outlook.
- Permite digitar ou selecionar no calendário a data inicial.
- Permite deixar o assunto vazio, digitar um trecho livre ou selecionar um tipo de notificação na lista suspensa editável.
- Converte cada opção visível em um ou mais termos internos e aceita a correspondência de qualquer termo configurado.
- Filtra mensagens por data, hora e, quando informado, por trecho do assunto.
- Restringe a pesquisa aos remetentes oficiais `ordersender-prod@ansmtp.ariba.com` e `petronect@petronect.com.br`.
- Extrai IDs no padrão `700` seguido de sete dígitos.
- Para `Sala`, separa tipo e mensagem das notificações Petronect e exporta o layout específico.
- Para assunto diferente ou vazio, exporta data, assunto, ID e o `Body` original sem tratamento.
- Sugere automaticamente `Downloads\emails_petronect.xlsx` como destino inicial, sem impedir a escolha de outro local ou nome.
- Verifica automaticamente a última versão publicada e oferece atualização quando necessário.
- Registra ambiente, critérios, contagens e erros detalhados no log.
- Permite cancelar a execução e abrir o Excel gerado.

<h2 id="logs-e-diagnóstico-de-datas">Logs e diagnóstico de datas</h2>

A data informada na interface é construída diretamente pelos componentes dia, mês, ano, hora e minuto; ela não depende do formato curto configurado no Windows. As datas COM do Outlook também são normalizadas pelos componentes `year`, `month` e `day`. Se uma integração devolver texto, valores inequívocos são reconhecidos automaticamente e valores ambíguos seguem explicitamente a localidade do Windows (`pt_BR` usa dia/mês e `en_US` usa mês/dia).

Para facilitar comparações entre computadores, o log registra:

- fuso horário, deslocamento UTC, localidade e codificação preferencial;
- formato fixo da interface e estratégia de normalização;
- menor e maior data de recebimento encontradas em cada pasta;
- quantidade de itens no período, anteriores ao corte, fora do assunto e que não são e-mails;
- classes MAPI e tipos de objeto usados para representar `ReceivedTime`;
- até três amostras estruturais por pasta com comprimentos do assunto, `Body` e `HTMLBody`, quantidade de anexos e tamanho em bytes.

As amostras não registram remetente, destinatários, texto do assunto nem conteúdo do e-mail. Quando todos os itens forem anteriores ao corte, o log informa explicitamente a data mais recente encontrada e que o filtro de assunto não chegou a ser aplicado.

<h2 id="última-release">Última release</h2>

A versão atual é **0.0.1.2**. A página abaixo contém o executável para Windows, as notas da versão e os arquivos-fonte correspondentes à tag publicada.

<p align="center">
  <a href="https://github.com/Marcus300/petronect-email-extractor/releases/latest"><strong>Acessar a página de download da última release »</strong></a>
</p>

As versões anteriores continuam disponíveis no [histórico completo de releases](https://github.com/Marcus300/petronect-email-extractor/releases).

<h2 id="roadmap">Roadmap</h2>

- [x] Incluir o remetente (`Sender`).
- [x] Disponibilizar uma lista suspensa editável com os assuntos padrão das notificações Petronect.
- [x] Restringir a pesquisa aos remetentes oficiais configurados.
- [x] Criar um layout genérico com `Body` original para pesquisas diferentes de `Sala`.
- [ ] Criar layouts tratados específicos para outros modelos de notificação Petronect.
- [ ] Implementar a fonte Microsoft Graph após aprovação e configuração do aplicativo no Microsoft Entra ID.

<h2 id="releases-e-versões-anteriores">Releases e versões anteriores</h2>

- [Baixar a versão mais recente](https://github.com/marcus300/petronect-email-extractor/releases/latest)
- [Consultar todas as versões](https://github.com/marcus300/petronect-email-extractor/releases)
- [Ler o histórico de alterações](CHANGELOG.md)

Para publicar uma versão, atualize `email_extractor/version.py` e `version_info.txt`, execute os testes e envie uma tag correspondente:

```powershell
git tag -a v0.0.1.2 -m "Petronect Email Extractor v0.0.1.2"
git push origin v0.0.1.2
```

O workflow testa o projeto no Windows, valida a correspondência entre tag e metadados, gera o `.exe` e o anexa à release. Nunca substitua uma tag publicada: cada nova versão deve receber uma nova tag, preservando downloads e notas anteriores.

<h2 id="segurança">Segurança</h2>

Consulte [`docs/SECURITY.md`](docs/SECURITY.md). Vulnerabilidades devem ser comunicadas diretamente ao mantenedor, sem abertura de issue pública.

<h2 id="código-de-conduta">Código de conduta</h2>

Consulte [`docs/CODE_OF_CONDUCT.md`](docs/CODE_OF_CONDUCT.md).

<h2 id="contribuição">Contribuição</h2>

Consulte [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md).

1. Implemente a alteração com mensagens de commit claras.
2. Execute todos os testes e valide o build.
3. Abra um Pull Request descrevendo a mudança e sua validação.

<h2 id="contato">Contato</h2>

- Principal: [marcus.brito@emerson.com](mailto:marcus.brito@emerson.com)
- Pessoal: [marcus300@gmail.com](mailto:marcus300@gmail.com)
- GitHub: [github.com/marcus300](https://github.com/marcus300)

<p align="center">Licença MIT · Copyright © 2026 Marcus Brito</p>
