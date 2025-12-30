# راهنمای نصب و اجرا روی VPS Hetzner

## 🚀 شروع سریع (Quick Start)

اگر با خطا مواجه شدید، این دستورات را اجرا کنید:

```bash
# 1. رفع مشکلات و نصب وابستگی‌ها
bash vps_quick_fix.sh

# 2. اجرای برنامه
bash run_vps.sh
```

یا به صورت دستی:
```bash
# راه‌اندازی virtual display
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
export DISPLAY=:99

# اجرای برنامه
python3 main.py
```

---

## پیش‌نیازها

### 1. سرور VPS
- Ubuntu 20.04 یا 22.04
- حداقل 2GB RAM
- IP تمیز (بدون تاریخچه spam/abuse)

### 2. دسترسی SSH
```bash
ssh root@your_vps_ip
```

## مراحل نصب

### 1. به‌روزرسانی سیستم
```bash
apt update && apt upgrade -y
```

### 2. نصب Python و ابزارهای مورد نیاز
```bash
apt install -y python3 python3-pip git wget curl unzip
```

### 3. نصب Chrome و ChromeDriver
```bash
# نصب Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb

# نصب وابستگی‌های Chrome برای headless mode و Xvfb برای pynput
apt install -y xvfb libxi6 libgconf-2-4 libnss3 libxss1 libappindicator3-1 libatk-bridge2.0-0 libgtk-3-0 x11-utils xserver-xephyr
```

### 4. کلون کردن پروژه
```bash
cd /root
git clone <your_repo_url>
cd autoGithubAccountCreator-main
```

یا آپلود فایل‌ها با scp:
```bash
# از کامپیوتر محلی
scp -r /path/to/project root@your_vps_ip:/root/
```

### 5. نصب وابستگی‌های Python
```bash
pip3 install -r requirements.txt
```

### 6. پیکربندی

#### تنظیم Headless Mode
فایل `main.py` را ویرایش کنید و در خط 1784 پارامتر `headless=True` اضافه کنید:

```python
# قبل:
self.setup_firefox_driver(use_proxy=True)

# بعد:
self.setup_firefox_driver(use_proxy=True, headless=True)
```

یا می‌توانید یک متغیر محیطی اضافه کنید:
```bash
export HEADLESS=true
```

#### تنظیم پروکسی (اختیاری)
فایل `proxy_config.json` را ویرایش کنید:
```json
{
  "proxy_enabled": false,
  "providers": {
    "free_proxy": {
      "enabled": false
    }
  }
}
```

**نکته**: اگر IP سرور تمیز است، پروکسی را غیرفعال کنید.

#### تنظیم CAPTCHA (اختیاری)
اگر CAPTCHA می‌خواهید:
```json
{
  "captcha_services": {
    "enabled": true,
    "primary_service": "2captcha",
    "2captcha": {
      "enabled": true,
      "api_key": "your_actual_api_key"
    }
  }
}
```

## اجرا

### حالت عادی (با Xvfb برای pynput)
```bash
# راه‌اندازی virtual display
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# اجرای برنامه
python3 main.py
```

یا در یک خط:
```bash
DISPLAY=:99 xvfb-run -a python3 main.py
```

### اجرا در پس‌زمینه با screen
```bash
# نصب screen
apt install -y screen

# ایجاد session جدید
screen -S github_bot

# راه‌اندازی virtual display و اجرای برنامه
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
python3 main.py

# جدا شدن از session: Ctrl+A سپس D
# بازگشت به session: screen -r github_bot
```

### اجرا با nohup
```bash
# راه‌اندازی Xvfb در پس‌زمینه
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &

# اجرای برنامه با DISPLAY
DISPLAY=:99 nohup python3 main.py > output.log 2>&1 &

# مشاهده لاگ
tail -f output.log
```

### اجرا با systemd (توصیه می‌شود)
ایجاد فایل سرویس:
```bash
nano /etc/systemd/system/github-bot.service
```

محتوای فایل:
```ini
[Unit]
Description=GitHub Account Creator Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/autoGithubAccountCreator-main
Environment="DISPLAY=:99"
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1920x1080x24
ExecStart=/usr/bin/python3 /root/autoGithubAccountCreator-main/main.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/github-bot.log
StandardError=append:/var/log/github-bot-error.log

[Install]
WantedBy=multi-user.target
```

فعال‌سازی و اجرا:
```bash
systemctl daemon-reload
systemctl enable github-bot
systemctl start github-bot

# مشاهده وضعیت
systemctl status github-bot

# مشاهده لاگ
tail -f /var/log/github-bot.log
```

## نکات مهم

### 1. IP تمیز
- از IP سرور Hetzner مستقیماً استفاده کنید
- IP نباید در blacklist باشد
- تست کنید: https://mxtoolbox.com/blacklists.aspx

### 2. Rate Limiting
- بین هر اکانت 5-10 دقیقه صبر کنید
- روزانه حداکثر 10-20 اکانت بسازید
- از proxy rotation استفاده کنید

### 3. مانیتورینگ
```bash
# مشاهده مصرف منابع
htop

# مشاهده فرآیندهای Chrome
ps aux | grep chrome

# مشاهده فضای دیسک
df -h

# پاکسازی profile‌های قدیمی
rm -rf browser_profiles/profile_*
```

### 4. امنیت
```bash
# فایروال
ufw allow 22/tcp
ufw enable

# تغییر پورت SSH (اختیاری)
nano /etc/ssh/sshd_config
# Port 2222
systemctl restart sshd
```

### 5. خطاهای رایج

#### Chrome crash
```bash
# افزایش shared memory
mount -o remount,size=2G /dev/shm
```

#### Out of memory
```bash
# ایجاد swap
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

#### Permission denied
```bash
chmod +x main.py
chown -R root:root /root/autoGithubAccountCreator-main
```

## تست اولیه

قبل از اجرای کامل، تست کنید:
```bash
# تست با 1 اکانت
python3 main.py
# وقتی پرسید: 1
```

اگر موفق بود، اکانت در `github_accounts.txt` ذخیره می‌شود.

## پشتیبان‌گیری

```bash
# پشتیبان از اکانت‌های ساخته شده
cp github_accounts.txt github_accounts_backup_$(date +%Y%m%d).txt

# پشتیبان از تنظیمات
tar -czf config_backup.tar.gz *.json *.txt
```

## توقف برنامه

```bash
# اگر با screen اجرا کردید
screen -r github_bot
# سپس Ctrl+C

# اگر با systemd اجرا کردید
systemctl stop github-bot

# اگر با nohup اجرا کردید
pkill -f main.py
```

## مشکلات و راه‌حل‌ها

### خطای pynput: "this platform is not supported"
این خطا به دلیل نبود X server است. راه‌حل:
```bash
# نصب Xvfb
apt install -y xvfb

# اجرا با virtual display
DISPLAY=:99 xvfb-run -a python3 main.py
```

### خطای ReadTimeoutError یا Chrome timeout
این خطا معمولاً به دلیل مشکل در راه‌اندازی Chrome است:
```bash
# 1. نصب وابستگی‌های کامل Chrome
apt install -y libnss3 libxss1 libasound2 libatk-bridge2.0-0 libgtk-3-0 libgbm1 fonts-liberation

# 2. پاکسازی فرآیندهای قدیمی
pkill -f chrome
pkill -f Xvfb

# 3. پاکسازی lock files
rm -rf browser_profiles/*/SingletonLock
rm -rf browser_profiles/*/SingletonSocket

# 4. اجرا با اسکریپت کمکی
bash vps_quick_fix.sh
bash run_vps.sh
```

یا استفاده از اسکریپت سریع:
```bash
# دانلود و اجرای fix script
bash vps_quick_fix.sh

# سپس اجرای برنامه
bash run_vps.sh
```

### هشدار urllib3 version mismatch
این فقط یک warning است و مشکلی ایجاد نمی‌کند. برای رفع:
```bash
pip3 install --upgrade urllib3 requests
```

### CAPTCHA زیاد می‌آید
- IP را تغییر دهید
- از proxy استفاده کنید
- سرویس CAPTCHA solving فعال کنید
- بین اکانت‌ها تاخیر بیشتری بگذارید

### Email verification نمی‌رسد
- سرویس mail.tm ممکن است down باشد
- چند دقیقه صبر کنید
- برنامه را restart کنید

### Chrome crash می‌کند
- RAM کافی نیست → swap اضافه کنید
- Shared memory کم است → افزایش دهید
- Profile‌های قدیمی را پاک کنید

## پشتیبانی

اگر مشکلی داشتید:
1. لاگ‌ها را بررسی کنید
2. Screenshot‌های خطا را چک کنید
3. IP را در blacklist بررسی کنید
