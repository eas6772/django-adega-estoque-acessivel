# Migração e Modernização de um Controle de Estoque para Arquitetura Web Acessível em Nuvem com Django

Este projeto consiste no desenvolvimento e modernização de um sistema de controle de estoque voltado para uma pequena adega de bairro. A aplicação evoluiu de um modelo anterior para uma arquitetura web moderna, escalável, integrada a APIs, hospedada na nuvem e projetada sob as diretrizes de acessibilidade digital.

---

## 🛠️ Tecnologias Utilizadas

O ecossistema do projeto foi construído utilizando tecnologias robustas e de mercado:

* **Back-end:** Python com framework Django
* **Banco de Dados:** PostgreSQL (Pronto para ambiente de produção e nuvem)
* **Front-end:** HTML5, CSS3 e JavaScript (Para interações dinâmicas na interface)
* **Acessibilidade:** Padrões WCAG / eMAG (Navegação por teclado, contrastes adequados e tags ARIA)
* **Infraestrutura:** Arquitetura Cloud (Deploy em nuvem e consumo de APIs externas)

---

## 🚀 Funcionalidades Principais

* **Gestão de Estoque:** Controle completo de entrada, saída, estoque mínimo e validade de produtos (vinhos, destilados, etc.).
* **Interface Inclusiva:** Recursos de acessibilidade integrados para garantir que qualquer usuário consiga operar o sistema sem barreiras.
* **Consumo de APIs:** Integração de serviços externos para enriquecer a experiência de uso e automação de processos.
* **Persistência Segura:** Arquitetura integrada ao PostgreSQL com migrações de dados estruturadas a partir do sistema antigo.

---

## 🔧 Como Executar o Projeto Localmente

### Pré-requisitos
* Python 3.10 ou superior
* PostgreSQL instalado e rodando localmente (ou container Docker)

### Passo a Passo

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com
   cd django-adega-estoque-acessivel
   ```

2. **Criar e ativar o ambiente virtual (venv):**
   ```bash
   python -m venv venv
   # No Windows:
   .\venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```

3. **Instalar as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar as variáveis de ambiente:**
   * Crie um arquivo `.env` na raiz do projeto e configure as credenciais do seu banco PostgreSQL (Database name, user, password, host, port).

5. **Executar as Migrations e iniciar o servidor:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
   Acesse `http://127.0.0` no seu navegador.

---

## 📝 Autoria e Contexto Acadêmico

Este repositório armazena o código-fonte referente ao trabalho de faculdade focado em Engenharia de Software, Migração de Sistemas e Inclusão Digital.
