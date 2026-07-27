FROM python:3.14-slim

# Evita a criação de arquivos .pyc e força a exibição imediata dos logs no terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação
COPY . .

EXPOSE 5000

# Comando para iniciar o servidor Flask
CMD ["python", "app.py"]