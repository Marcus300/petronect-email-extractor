# Política de Segurança

## 🔐 Reportando Vulnerabilidades

Se você descobrir uma vulnerabilidade de segurança neste projeto:

1. **Não abra uma issue pública.**
2. Envie um e-mail diretamente para o mantenedor responsável (ou canal seguro definido no projeto).
3. Forneça o máximo de detalhes possível:

   * Descrição da falha
   * Etapas para reprodução
   * Impacto potencial
   * Qualquer sugestão de correção ou mitigação

---

## 🔒 Boas Práticas Adotadas

Este projeto aplica as seguintes medidas para minimizar riscos:

* O projeto não solicita nem armazena credenciais do Outlook.
* O acesso ocorre pelo perfil local já autenticado no Outlook desktop.
* O `.gitignore` impede o versionamento de arquivos locais, planilhas e logs.
* A verificação de atualizações acessa somente a API pública de releases do repositório oficial.

---

## 🚫 Evite

* Versionar arquivos `.env` contendo senhas ou tokens
* Armazenar caminhos de rede ou diretórios de usuários reais em arquivos públicos
* Compartilhar capturas de tela com dados confidenciais

---

## ✅ Recomendado

* Rotacionar credenciais periodicamente
* Revisar planilhas e logs antes de compartilhá-los, pois podem conter dados de mensagens.
* Manter `pywin32`, `openpyxl` e PyInstaller atualizados e testados.

---

## 📬 Contato Seguro

Relatórios podem ser enviados para: `marcus.brito@emerson.com` ou por canal seguro descrito no repositório.

---

Agradecemos por sua colaboração com a segurança deste projeto!
