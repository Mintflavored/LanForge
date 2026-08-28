# 🎮 LANForge — P2P Virtual LAN & Host Hub for Gaming

**LANForge** — это современная, быстрая и легковесная замена **Radmin VPN** и **Hamachi**, разработанная специально для комфортной игры с друзьями по сети через интернет.

---

## ⚡ Преимущества и ключевые особенности

- 🚀 **1-Click Game Rooms:** Создание комнат с 6-значными кодами (`ABC-XYZ`) или подключение по invite-ссылке без ручной возни со сложными настройками.
- 📡 **Magic LAN Discovery (Broadcast Relay):** Перехват и ретрансляция широковещательных пакетов `UDP 255.255.255.255` и Multicast. Игры (Minecraft, Terraria, CS, Source, Factorio и др.) **автоматически появляются во вкладке «Локальная игра»** у всех друзей в комнате!
- 🛡️ **Двойной режим туннелирования (Hybrid):**
  - **Wintun Virtual L3 Adapter:** Полноценная виртуальная сеть `10.42.0.0/24` на базе сверхбыстрого драйвера Wintun (от команды WireGuard).
  - **Zero-Driver Port Forward Mode:** Режим без установки драйверов и без прав администратора — прямое P2P проксирование портов.
- 🌐 **NAT Traversal & UPnP IGD:**
  - Автоматический маппинг портов на домашнем роутере через UPnP/NAT-PMP.
  - Детекция типа NAT по STUN (RFC 5389) и прямое UDP Hole Punching.
  - Встроенный зашифрованный Relay Fallback для симметричных NAT.
- 🎯 **Каталог 30+ игровых пресетов:** Готовые порты, инструкции и 1-клик хостинг для Minecraft, Terraria, Palworld, CS, Valheim, Stardew Valley, Factorio, HOMM III и других.
- 💬 **Комнатный чат и живой HUD:** Мониторинг RTT пинга до каждого друга в миллисекундах, удобное копирование `IP:Port` для прямого подключения в консоли игры.

---

## 🏗️ Структура проекта

```
lanforge/
├── packages/
│   ├── server/           # Signaling, Room Lobby & Relay Server (Node.js/TypeScript + WebSockets)
│   │   ├── src/
│   │   │   ├── rooms.ts  # Управление комнатами и пулом IP 10.42.0.x
│   │   │   ├── server.ts # WebSocket сервер и HTTP health-check
│   │   │   └── types.ts
│   │   └── tests/        # Unit & E2E тесты
│   │
│   └── app/              # Desktop App (Tauri v2 + Rust + React + TailwindCSS)
│       ├── src-tauri/    # Rust нативное сетевое ядро (STUN, UPnP, Broadcast Forwarder, Wintun)
│       └── src/          # React Dark Gaming UI (Комнаты, Пресеты, Радар, Диагностика NAT)
└── package.json
```

---

## 🚀 Быстрый старт

### 1. Запуск сигнального сервера:
```bash
npm run dev:server
# Сервер запустится на http://localhost:8787
```

### 2. Запуск веб-клиента / Desktop UI:
```bash
npm run dev:app
# Интерфейс откроется на http://localhost:1420
```

### 3. Запуск нативного десктопного приложения (Tauri):
```bash
npm run tauri:dev
```

### 4. Запуск тестов:
```bash
npm run test:server
```
