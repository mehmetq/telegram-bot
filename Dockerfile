FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Chrome için GPG key'i manuel olarak ekle
RUN mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/google-chrome.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Chrome yükle
RUN apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ChromeDriver'ı doğru şekilde indir
RUN CHROME_MAJOR_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1) \
    && echo "Chrome major version: $CHROME_MAJOR_VERSION" \
    && CHROME_DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_MAJOR_VERSION") \
    && echo "ChromeDriver version: $CHROME_DRIVER_VERSION" \
    && wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip" \
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
