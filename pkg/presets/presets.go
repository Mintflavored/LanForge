package presets

// GamePreset contains connection metadata for multiplayer games.
type GamePreset struct {
	ID                    string `json:"id"`
	Name                  string `json:"name"`
	Category              string `json:"category"`
	DefaultPort           int    `json:"defaultPort"`
	Protocol              string `json:"protocol"` // "tcp", "udp", "both"
	Color                 string `json:"color"`
	LanDiscoverySupported bool   `json:"lanDiscoverySupported"`
	DiscoveryPort         int    `json:"discoveryPort,omitempty"`
	Description           string `json:"description"`
	ConnectHint           string `json:"connectHint"`
}

// AllPresets is the predefined catalog of games supported by LANForge.
var AllPresets = []GamePreset{
	{
		ID:                    "minecraft_java",
		Name:                  "Minecraft (Java Edition)",
		Category:              "Sandbox",
		DefaultPort:           25565,
		Protocol:              "tcp",
		Color:                 "#22c55e",
		LanDiscoverySupported: true,
		DiscoveryPort:         4445,
		Description:           "Открой мир для сети в игре — сервер автоматически появится у друзей!",
		ConnectHint:           "Сетевая игра -> Прямое подключение -> {HOST_IP}:25565",
	},
	{
		ID:                    "terraria",
		Name:                  "Terraria",
		Category:              "Sandbox",
		DefaultPort:           7777,
		Protocol:              "tcp",
		Color:                 "#10b981",
		LanDiscoverySupported: true,
		Description:           "Кооперативное выживание. Создай сервер через меню игры или TerrariaServer.exe.",
		ConnectHint:           "Многопользовательская игра -> Присоединиться по IP -> {HOST_IP} -> Порт 7777",
	},
	{
		ID:                    "palworld",
		Name:                  "Palworld",
		Category:              "Survival",
		DefaultPort:           8211,
		Protocol:              "udp",
		Color:                 "#3b82f6",
		LanDiscoverySupported: false,
		Description:           "Выживание с питомцами на выделенном или совместном локальном сервере.",
		ConnectHint:           "Присоединиться к мультиплееру -> ввести {HOST_IP}:8211 внизу экрана",
	},
	{
		ID:                    "cs_source",
		Name:                  "Counter-Strike / Source Games",
		Category:              "FPS",
		DefaultPort:           27015,
		Protocol:              "udp",
		Color:                 "#f59e0b",
		LanDiscoverySupported: true,
		DiscoveryPort:         27015,
		Description:           "CS 1.6, CS:Source, Half-Life 2, Left 4 Dead 2, Garry's Mod.",
		ConnectHint:           "В консоли игры: connect {HOST_IP}:27015 или вкладка LAN в Find Servers",
	},
	{
		ID:                    "valheim",
		Name:                  "Valheim",
		Category:              "Survival",
		DefaultPort:           2456,
		Protocol:              "udp",
		Color:                 "#eab308",
		LanDiscoverySupported: false,
		Description:           "Скандинавский кооперативный симулятор выживания в чистилище.",
		ConnectHint:           "Start Game -> Start Server / Присоединиться по IP -> {HOST_IP}:2456",
	},
	{
		ID:                    "stardew_valley",
		Name:                  "Stardew Valley",
		Category:              "Sandbox",
		DefaultPort:           24642,
		Protocol:              "udp",
		Color:                 "#ec4899",
		LanDiscoverySupported: true,
		Description:           "Уютная фермерская RPG для 1-8 игроков.",
		ConnectHint:           "Совместная игра -> Вступить в игру по LAN -> {HOST_IP}",
	},
	{
		ID:                    "factorio",
		Name:                  "Factorio",
		Category:              "Sandbox",
		DefaultPort:           34197,
		Protocol:              "udp",
		Color:                 "#f97316",
		LanDiscoverySupported: true,
		DiscoveryPort:         34197,
		Description:           "Автоматизация и строительство фабрик. Полная поддержка автопоиска LAN!",
		ConnectHint:           "Сетевая игра -> Локальная игра (LAN) или Подключиться к адресу -> {HOST_IP}:34197",
	},
	{
		ID:                    "project_zomboid",
		Name:                  "Project Zomboid",
		Category:              "Survival",
		DefaultPort:           16261,
		Protocol:              "udp",
		Color:                 "#ef4444",
		LanDiscoverySupported: false,
		Description:           "Хардкорное выживание во время зомби-апокалипсиса.",
		ConnectHint:           "Войти на сервер -> Добавить сервер -> IP: {HOST_IP}, Порт: 16261",
	},
	{
		ID:                    "dont_starve",
		Name:                  "Don't Starve Together",
		Category:              "Survival",
		DefaultPort:           10999,
		Protocol:              "udp",
		Color:                 "#d97706",
		LanDiscoverySupported: true,
		Description:           "Выживайте вместе в темном процедурно-генерируемом мире.",
		ConnectHint:           "Просмотр игр -> Фильтр: Только LAN -> Сервер хоста появится в списке",
	},
	{
		ID:                    "homm3",
		Name:                  "Heroes of Might and Magic III",
		Category:              "Classic",
		DefaultPort:           2300,
		Protocol:              "both",
		Color:                 "#a855f7",
		LanDiscoverySupported: true,
		Description:           "Легендарная пошаговая стратегия (HotA / HD Mod). TCP/IP игра.",
		ConnectHint:           "Новая игра -> Многопользовательская -> TCP/IP -> Ввести {HOST_IP}",
	},
	{
		ID:                    "worms_armageddon",
		Name:                  "Worms Armageddon",
		Category:              "Classic",
		DefaultPort:           17011,
		Protocol:              "tcp",
		Color:                 "#84cc16",
		LanDiscoverySupported: true,
		Description:           "Культовая битва червячков с базуками и банана-бомбами по Direct IP.",
		ConnectHint:           "Сетевая игра -> Direct IP -> Ввести {HOST_IP}",
	},
	{
		ID:                    "assetto_corsa",
		Name:                  "Assetto Corsa",
		Category:              "Racing",
		DefaultPort:           9600,
		Protocol:              "both",
		Color:                 "#06b6d4",
		LanDiscoverySupported: false,
		Description:           "Реалистичный автосимулятор. Сервер поднимается через acServer.exe.",
		ConnectHint:           "Content Manager -> Drive -> LAN -> Сервер хоста",
	},
}

// FindPreset looks up a game preset by ID.
func FindPreset(id string) *GamePreset {
	for i := range AllPresets {
		if AllPresets[i].ID == id {
			return &AllPresets[i]
		}
	}
	return nil
}
