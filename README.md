# WhatsApp Guia Sender

Este projeto implementa um pequeno sistema para envio automático de guias (PDF) via WhatsApp Web.

## Requisitos
- Python 3.10+
- Google Chrome e driver do Chrome compatível (`chromedriver` no PATH)
- Dependências Python listadas em `requirements.txt`

## Instalação
```bash
pip install -r requirements.txt
```

## Utilização
1. Coloque seus arquivos PDF na pasta `guias/`.
2. Preencha `contacts.csv` com duas colunas: `document` (CNPJ ou CPF sem formatação) e `phone` (número completo com código do país, ex. +5511999999999).
3. Execute o programa:
```bash
python main.py
```
4. Será aberto o WhatsApp Web no navegador. Faça a leitura do QR code uma única vez e aguarde o envio dos arquivos.

O script identifica o CPF ou CNPJ dentro de cada PDF, busca o telefone correspondente e envia o arquivo para o contato.
