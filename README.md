# Pilates Studio Manager

Sistema simples em Flask para organização de agenda e controle de recebimentos em estúdios de pilates. Funciona em ambiente local usando SQLite.

## Instalação

1. Certifique-se de ter o Python 3 instalado.
2. Opcionalmente crie um ambiente virtual:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
4. Inicialize o banco de dados:
   ```
   flask init-db
   ```
5. Inicie o servidor local:
   ```
   flask run
   ```

A aplicação estará disponível em `http://localhost:5000`.

## Funcionalidades básicas

- Cadastro de alunos e instrutores.
- Agendamento de aulas.
- Registro de pagamentos.
- Visualização rápida das informações mais importantes em telas simples.
