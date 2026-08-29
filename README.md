<div align="center">

![LANForge Banner](discord_banner.png)

# LANForge

Простой эмулятор локальной сети (LAN) для совместной игры через интернет по прямым P2P-соединениям (UDP).

[![Release](https://img.shields.io/github/v/release/NERVS-DEV/LANForge?style=flat-square&color=ff5500)](https://github.com/NERVS-DEV/LANForge/releases)
[![Go Version](https://img.shields.io/badge/Go-1.24-00ADD8?style=flat-square&logo=go)](https://go.dev)
[![Python Version](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows_x64-0078D6?style=flat-square&logo=windows)](https://github.com/NERVS-DEV/LANForge/releases)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[**Скачать LANForge.exe**](https://github.com/NERVS-DEV/LANForge/releases/latest) • [**Быстрый старт**](#быстрый-старт) • [**Пресеты игр**](#пресеты-игр) • [**Свой сервер**](#развертывание-сигналинг-сервера)

</div>

---

## Особенности

- **Прямое соединение (P2P по UDP):** Трафик игры идет напрямую между игроками, без проксирующих реле-серверов.
- **Один исполняемый файл:** Не требует установки драйверов виртуальных адаптеров (TUN/TAP) и прав администратора.
- **Не конфликтует с VPN и прокси:** Работает параллельно с Clash, системными VPN и локальными прокси.
- **Discord Rich Presence:** Показывает в профиле Discord статус игры, название комнаты и число участников.
- **LAN Радар:** Автоматически находит открытые локальные миры (Minecraft, Source-игры) и позволяет скопировать адрес в один клик.
- **Гибридный сигналинг:** Можно играть через встроенный локальный сервер, общий облачный сервер или поднять свой на VPS.

---

## Быстрый старт

1. Скачайте [`LANForge.exe`](https://github.com/NERVS-DEV/LANForge/releases/latest) (или zip-архив).
2. Запустите приложение.

**Для хоста (создателя):**
1. Нажмите **«+ Создать сеть»**.
2. Выберите игру и скопируйте 6-значный код комнаты (например, `LAN-4821`).
3. Передайте код друзьям.

**Для подключающихся:**
1. Нажмите **«Войти по коду»** и введите полученный код.
2. В игре подключитесь к виртуальному IP хоста (например, `10.42.0.1:25565`).

---

## Пресеты игр

| Игра | Порт | Протокол | Как подключиться |
| :--- | :---: | :---: | :--- |
| **Minecraft (Java Edition)** | `25565` | TCP | Сетевая игра -> По адресу -> `{IP_хоста}:25565` |
| **Terraria** | `7777` | TCP | Мультиплеер -> По IP -> `{IP_хоста}:7777` |
| **Palworld** | `8211` | UDP | Мультиплеер -> `{IP_хоста}:8211` |
| **Counter-Strike / Source** | `27015` | UDP | Консоль: `connect {IP_хоста}:27015` |
| **Valheim** | `2456` | UDP | Присоединиться по IP -> `{IP_хоста}:2456` |
| **Stardew Valley** | `24642` | UDP | Совместная игра -> Вступить по LAN |
| **Factorio** | `34197` | UDP | Сетевая игра -> Локальная игра (LAN) |
| **Project Zomboid** | `16261` | UDP | Войти на сервер -> `{IP_хоста}:16261` |
| **Don't Starve Together** | `10999` | UDP | Просмотр игр -> Фильтр LAN |
| **Heroes of Might & Magic III**| `2300` | TCP | Многопользовательская -> TCP/IP |

---

## Развертывание сигналинг-сервера

Сервер сигналинга только помогает игрокам обменяться пирами и не передает игровой трафик. Потребляет ~10 МБ RAM.

### Вариант 1: Docker
```bash
docker build -t lanforge-server .
docker run -d -p 8787:8787 --name lanforge lanforge-server
```

### Вариант 2: Бесплатный хостинг (Render.com)
В репозитории уже есть `render.yaml`. При подключении репозитория к Render он автоматически развернет сервис с поддержкой WebSockets.

---

## Сборка из исходников

### Требования:
- Go 1.24+
- Python 3.12+

```powershell
# Клонирование
git clone https://github.com/NERVS-DEV/LANForge.git
cd LANForge

# Сборка Go-сервера
go build -ldflags="-w -s" -o bin/lanforge-server.exe ./cmd/server

# Установка зависимостей Python
pip install pyinstaller pywebview pystray pillow pythonnet clr_loader

# Сборка одиночного exe
python -m PyInstaller --noconsole --onefile --clean --name "LANForge" --icon app.ico --add-data "ui;ui" --add-data "app_icon.png;." --add-data "discord_banner.png;." --add-binary "bin/lanforge-server.exe;." --collect-all webview --collect-all pystray --collect-all PIL --collect-all clr_loader --collect-all pythonnet lanforge_gui.py --distpath ./dist
```

---

## Лицензия

[MIT](LICENSE) © NERVS
