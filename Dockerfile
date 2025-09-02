FROM selenium/standalone-chrome:latest

USER root
WORKDIR /app

# Python kurulumu
RUN apt-get update && apt-get install -y python3 python3-pip

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1

# Railway debug için bash fallback
CMD ["bash", "-c", "python3 -m telegram_bot || tail -f /dev/null"]
