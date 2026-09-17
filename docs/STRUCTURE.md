# Estrutura do projeto

```text
sala/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # Testes em pushes e pull requests
│   │   └── release.yml         # Build e publicação a partir de tags
│   └── release.yml             # Categorias das notas automáticas
├── docs/
│   ├── logo/
│   │   ├── logo.ico            # Ícone das janelas e do executável
│   │   └── logo.png            # Logo exibido na janela Sobre e no README
│   ├── CODE_OF_CONDUCT.md
│   ├── CONTRIBUTING.md
│   ├── FLUXOGRAMA.mmd
│   ├── SECURITY.md
│   └── STRUCTURE.md
├── email_extractor/
│   ├── cleaning.py             # Limpeza do conteúdo e extração do ID
│   ├── calendar_model.py       # Cálculos do calendário PT-BR iniciado no domingo
│   ├── diagnostics.py          # Metadados e logs de falha
│   ├── export.py               # Geração atômica do Excel
│   ├── models.py               # Modelos de dados
│   ├── localization.py         # Textos PT-BR e ordenação alfabética determinística
│   ├── outlook.py              # Leitura recursiva do Outlook
│   ├── paths.py                # Pastas do usuário e destino padrão do Excel
│   ├── petronect.py            # Interpretação das notificações
│   ├── purchase_order.py       # Parser de pedidos SAP Business Network / Ariba
│   ├── ui.py                   # Interface gráfica
│   ├── update_checker.py       # Consulta da release mais recente no GitHub
│   └── updater.py              # Download, validação e substituição segura do executável
├── tests/                      # Testes automatizados
├── scripts/
│   └── verify_release.py       # Confere tag e metadados de versão
├── .gitignore
├── CHANGELOG.md                # Histórico visível de versões
├── LICENSE                     # Licença MIT
├── build_exe.ps1               # Geração do executável com PyInstaller
├── main.py                     # Ponto de entrada
├── README.md
├── requirements.txt
└── version_info.txt
```

`build/`, `dist/`, ambientes virtuais, caches, arquivos `.spec`, planilhas e logs são artefatos locais ignorados pelo Git.
