# APLICAÇÃO SIMULADOR COMPUTACIONAL

Este é um projeto de simulação de suporte online usando SimPy e Flask, onde são simulados atendimentos de suporte baseados em dados de tempo entre chegadas e tempo de serviço.

## Requisitos

- Python 3.12 ou superior
- R-base

## Instalação

1. **Clonar o repositório:**
```bash
git clone https://github.com/JoiceColling/Simulador.git
```

2. **Instalar as dependências da aplicação:**

Certifique-se de estar no diretório raiz do projeto e execute o comando:

Dependencias do App:

```bash
pip install -r requirements.txt
```

Dependencias do R:
```bash
Rscript install_r_packages.R
```
Garantir que o R esteja instalado:

```bash
R --version
```
Isso instalará todas as dependências necessárias para rodar o projeto.

## Executar o Projeto

1. **Iniciar o servidor Flask:**

No terminal, em ``../app``, dentro do diretório do projeto, execute:

```bash
flask run
```

2. **Acessar o simulador:**

Abra um navegador web e vá para:
```bash
http://localhost:5000/
```