FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Chrome için GPG key'i ekle ve Chrome kaynaklarını ayarla
RUN mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/google-chrome.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Chrome'un belirli bir sürümünü yükle (118 sürümü sabit)
RUN apt-get update \
    && apt-get install -y google-chrome-stable=118.0.5993.70-1 \
    && rm -rf /var/lib/apt/lists/*

# Chromedriver (118 sürümü) indir ve kur
RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/118.0.5993.70/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/bin/chromedriver

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Port ayarı
EXPOSE 8000

# Uygulamayı çalıştır
CMD ["python", "-m", "telegram_bot"]
