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

* O projeto não solicita nem armazena senhas do Outlook ou do Microsoft 365.
* A fonte clássica usa o perfil local do Outlook; a fonte Graph usa autenticação delegada MSAL com WAM no Windows, compatível com MFA, identidade do dispositivo e Conditional Access.
* O cache Graph é persistido no perfil do usuário e protegido pela Data Protection API do Windows.
* O aplicativo desktop é cliente público: nenhum `client_secret` deve ser criado, distribuído ou versionado.
* `client_id`, `tenant_id` e endereços das caixas homologadas são configurações públicas incorporadas ao executável; autenticação, MFA, consentimento e permissões de caixa continuam obrigatórios.
* O `.gitignore` impede o versionamento de arquivos locais, planilhas e logs.
* A verificação de atualizações acessa somente a API pública de releases do repositório oficial.

---

## 🚫 Evite

* Versionar arquivos `.env`, `graph_config.json` ou caches contendo identificadores locais ou tokens
* Armazenar caminhos de rede ou diretórios de usuários reais em arquivos públicos
* Compartilhar capturas de tela com dados confidenciais

---

## ✅ Recomendado

* Rotacionar credenciais periodicamente
* Revisar planilhas e logs antes de compartilhá-los, pois podem conter dados de mensagens.
* Manter `pywin32`, `openpyxl`, MSAL, MSAL Extensions e PyInstaller atualizados e testados.

---

## 📬 Contato Seguro

Relatórios podem ser enviados para: `marcus.brito@emerson.com` ou por canal seguro descrito no repositório.

---

Agradecemos por sua colaboração com a segurança deste projeto!
