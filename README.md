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
  <img src="https://img.shields.io/badge/versão-0.0.1.0-blue" alt="Versão 0.0.1.0">
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
- [Como usar](#como-usar)
- [Funcionalidades](#funcionalidades)
- [Testes](#testes)
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

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

<h3 id="atualizações-pelo-github">Atualizações pelo GitHub</h3>

A aplicação consulta em segundo plano a API pública de `marcus300/petronect-email-extractor/releases/latest`. Quando uma versão numericamente superior estiver disponível, o usuário poderá abrir sua página de download. A consulta também pode ser iniciada manualmente no About e não exige token ou credenciais.

<h2 id="como-usar">Como usar</h2>

```powershell
.\.venv\Scripts\python.exe main.py
```

Para gerar o executável:

```powershell
.\build_exe.ps1
```

O executável é criado em `dist/Petronect Email Extractor v0.0.1.0.exe`. O usuário escolhe o destino da planilha; o log é salvo ao lado dela com o sufixo `_log.txt`. Falhas de inicialização são registradas em `%LOCALAPPDATA%\PetronectEmailExtractor\logs`.

<h2 id="funcionalidades">Funcionalidades</h2>

- Seleciona caixas, pastas e subpastas do Outlook.
- Permite digitar ou selecionar no calendário a data inicial.
- Filtra mensagens por data, hora e trecho do assunto.
- Extrai IDs no padrão `700` seguido de sete dígitos.
- Separa tipo e conteúdo das notificações Petronect.
- Exporta data, assunto, ID, tipo e mensagem para Excel.
- Registra ambiente, critérios, contagens e erros detalhados no log.
- Permite cancelar a execução e abrir o Excel gerado.

<h2 id="testes">Testes</h2>

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

<h2 id="releases-e-versões-anteriores">Releases e versões anteriores</h2>

- [Baixar a versão mais recente](https://github.com/marcus300/petronect-email-extractor/releases/latest)
- [Consultar todas as versões](https://github.com/marcus300/petronect-email-extractor/releases)
- [Ler o histórico de alterações](CHANGELOG.md)

Para publicar uma versão, atualize `email_extractor/version.py` e `version_info.txt`, execute os testes e envie uma tag correspondente:

```powershell
git tag -a v0.0.1.0 -m "Petronect Email Extractor v0.0.1.0"
git push origin v0.0.1.0
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
