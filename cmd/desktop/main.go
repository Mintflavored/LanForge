//go:build windows

package main

import (
	"bytes"
	_ "embed"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"runtime/debug"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"

	webview2 "github.com/jchv/go-webview2"
	"github.com/lanforge/lanforge/pkg/discord"
	"github.com/lanforge/lanforge/pkg/server"
	"golang.org/x/sys/windows"
)

//go:embed ui/index.html
var embeddedHTML []byte

//go:embed bin/steam_api64.dll
var embeddedSteamDLL []byte

var (
	appVersion = "2.3.0"

	psapi               = syscall.NewLazyDLL("psapi.dll")
	procEmptyWorkingSet = psapi.NewProc("EmptyWorkingSet")

	appDataDir string
	configFile string
	logFile    string
	logMu      sync.Mutex

	discordClient *discord.Client
)

func init() {
	appData := os.Getenv("APPDATA")
	if appData == "" {
		appData = os.Getenv("USERPROFILE")
	}
	appDataDir = filepath.Join(appData, "LANForge")
	_ = os.MkdirAll(appDataDir, 0755)
	configFile = filepath.Join(appDataDir, "config.json")
	logFile = filepath.Join(appDataDir, "lanforge.log")

	// Распаковываем steam_api64.dll в AppData, если её там ещё нет
	dllTarget := filepath.Join(appDataDir, "steam_api64.dll")
	if fi, err := os.Stat(dllTarget); os.IsNotExist(err) || fi.Size() == 0 {
		_ = os.WriteFile(dllTarget, embeddedSteamDLL, 0755)
	}
}

func logMessage(level, tag, message string) {
	logMu.Lock()
	defer logMu.Unlock()

	ts := time.Now().Format("2006-01-02 15:04:05.000")
	line := fmt.Sprintf("[%s] [%s] [%s] %s\n", ts, strings.ToUpper(level), tag, message)

	f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err == nil {
		_, _ = f.WriteString(line)
		_ = f.Close()
	}
}

func getChildPIDs(parentPID uint32) []uint32 {
	snapshot, err := windows.CreateToolhelp32Snapshot(windows.TH32CS_SNAPPROCESS, 0)
	if err != nil {
		return nil
	}
	defer windows.CloseHandle(snapshot)

	var entry windows.ProcessEntry32
	entry.Size = uint32(unsafe.Sizeof(entry))

	childrenMap := make(map[uint32][]uint32)
	if err := windows.Process32First(snapshot, &entry); err == nil {
		for {
			ppid := entry.ParentProcessID
			pid := entry.ProcessID
			childrenMap[ppid] = append(childrenMap[ppid], pid)
			if err := windows.Process32Next(snapshot, &entry); err != nil {
				break
			}
		}
	}

	var descendants []uint32
	toVisit := []uint32{parentPID}
	for len(toVisit) > 0 {
		curr := toVisit[0]
		toVisit = toVisit[1:]
		for _, child := range childrenMap[curr] {
			descendants = append(descendants, child)
			toVisit = append(toVisit, child)
		}
	}
	return descendants
}

func trimMemory() {
	runtime.GC()
	debug.FreeOSMemory()

	myPID := uint32(os.Getpid())
	pids := append(getChildPIDs(myPID), myPID)

	for _, pid := range pids {
		h, err := windows.OpenProcess(windows.PROCESS_SET_QUOTA|windows.PROCESS_QUERY_INFORMATION, false, pid)
		if err == nil {
			_, _, _ = procEmptyWorkingSet.Call(uintptr(h))
			_ = windows.CloseHandle(h)
		}
	}
}

func main() {
	// 1. Ограничение ресурсов Go рантайма
	runtime.GOMAXPROCS(2)
	debug.SetMemoryLimit(16 * 1024 * 1024)
	debug.SetGCPercent(50)

	logMessage("INFO", "Init", fmt.Sprintf("=== LANForge v%s Pure Go Desktop Starting ===", appVersion))

	// 2. Инициализация Discord RPC
	discordClient = discord.NewClient()
	defer discordClient.Close()
	discordClient.SetActivity("В главном меню", fmt.Sprintf("P2P Virtual Gaming Hub v%s", appVersion), 0, 16, "", "")

	// 3. Запуск in-process сервера LANForge на порту 8787
	srv := server.NewServer(8787)
	srvHandler := srv.Handler()

	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" || r.URL.Path == "/index.html" {
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			w.Header().Set("Cache-Control", "no-cache")
			_, _ = w.Write(embeddedHTML)
			return
		}
		srvHandler.ServeHTTP(w, r)
	})

	go func() {
		if err := http.ListenAndServe("127.0.0.1:8787", mux); err != nil {
			logMessage("ERROR", "Server", fmt.Sprintf("In-process server error: %v", err))
		}
	}()

	// Даем серверу долю секунды на открытие сокета
	time.Sleep(100 * time.Millisecond)

	// 4. Настройка флагов WebView2 для минимизации RAM
	proxyBypass := "localhost,127.0.0.1,::1,10.0.0.0/8,192.168.0.0/16,172.16.0.0/12,*.local,10.42.*"
	_ = os.Setenv("NO_PROXY", proxyBypass)
	_ = os.Setenv("no_proxy", proxyBypass)

	browserArgs := strings.Join([]string{
		"--proxy-bypass-list=" + proxyBypass,
		"--disable-web-security",
		"--allow-file-access-from-files",
		"--disable-gpu",
		"--disable-gpu-compositing",
		"--enable-low-end-device-mode",
		"--renderer-process-limit=1",
		"--js-flags=--optimize_for_size\\ --lite-mode",
		"--disk-cache-size=1",
		"--media-cache-size=1",
		"--disable-background-networking",
		"--disable-component-update",
		"--disable-sync",
		"--disable-features=Translate,OptimizationHints,MediaRouter,CalculateNativeWinOcclusion,InterestFeedContentSuggestions,ElasticOverscroll,AudioServiceOutOfProcess",
	}, " ")
	_ = os.Setenv("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", browserArgs)

	// 5. Создание окна Edge WebView2
	w := webview2.NewWithOptions(webview2.WebViewOptions{
		Debug:     false,
		AutoFocus: true,
		DataPath:  filepath.Join(appDataDir, "EBWebView"),
		WindowOptions: webview2.WindowOptions{
			Title:     "LANForge",
			Width:     1040,
			Height:    660,
			IconId:    0,
			Center:    true,
		},
	})
	if w == nil {
		logMessage("ERROR", "WebView2", "Failed to initialize WebView2 window")
		return
	}
	defer w.Destroy()

	w.SetTitle("LANForge")
	w.SetSize(1040, 660, webview2.HintNone)

	// 6. Регистрация двустороннего Go <-> JavaScript моста (совместимость с pywebview API)
	w.Bind("goLog", func(level, tag, msg string) {
		logMessage(level, tag, msg)
	})

	w.Bind("goGetAppVersion", func() string {
		return appVersion
	})

	w.Bind("goGetConfig", func() string {
		data, err := os.ReadFile(configFile)
		if err != nil {
			return "{}"
		}
		return string(data)
	})

	w.Bind("goSaveConfig", func(cfgStr string) bool {
		err := os.WriteFile(configFile, []byte(cfgStr), 0644)
		return err == nil
	})

	w.Bind("goOpenLogDir", func() bool {
		_ = exec.Command("explorer", appDataDir).Start()
		return true
	})

	w.Bind("goGetLogContent", func() string {
		data, err := os.ReadFile(logFile)
		if err != nil {
			return "Лог-файл пуст."
		}
		lines := strings.Split(string(data), "\n")
		if len(lines) > 250 {
			lines = lines[len(lines)-250:]
		}
		return strings.Join(lines, "\n")
	})

	w.Bind("goUpdatePresence", func(details, state string, partySize, partyMax int, roomCode, gamePreset string) {
		if discordClient != nil {
			discordClient.SetActivity(details, state, partySize, partyMax, roomCode, gamePreset)
		}
	})

	w.Bind("goUpdateTray", func(statusText, ip string) {
		w.Dispatch(func() {
			if ip != "" && ip != "10.42.0.1" {
				w.SetTitle(fmt.Sprintf("LANForge — %s [%s]", statusText, ip))
			} else {
				w.SetTitle("LANForge")
			}
		})
	})

	w.Bind("goShowNotification", func(title, msg string) {
		logMessage("INFO", "Notify", fmt.Sprintf("%s: %s", title, msg))
	})

	w.Bind("goSteamGetStatus", func() string {
		resp, err := http.Get("http://127.0.0.1:8787/api/steam/status")
		if err != nil {
			res, _ := json.Marshal(map[string]interface{}{"steamRunning": false, "tunnelActive": false})
			return string(res)
		}
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		return string(body)
	})

	w.Bind("goSteamStart", func() string {
		resp, err := http.Post("http://127.0.0.1:8787/api/steam/start", "application/json", bytes.NewReader([]byte("{}")))
		if err != nil {
			res, _ := json.Marshal(map[string]interface{}{"ok": false, "error": err.Error()})
			return string(res)
		}
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		return string(body)
	})

	w.Bind("goSteamStop", func() string {
		resp, err := http.Post("http://127.0.0.1:8787/api/steam/stop", "application/json", bytes.NewReader([]byte("{}")))
		if err != nil {
			res, _ := json.Marshal(map[string]interface{}{"ok": false, "error": err.Error()})
			return string(res)
		}
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		return string(body)
	})

	w.Bind("goSteamApi", func(endpoint, payloadStr string) string {
		ep := endpoint
		switch ep {
		case "/api/share":
			ep = "/api/steam/host"
		case "/api/connect":
			ep = "/api/steam/connect"
		case "/api/invite":
			ep = "/api/steam/invite"
		case "/api/state":
			ep = "/api/steam/status"
		default:
			if !strings.HasPrefix(ep, "/api/steam/") {
				ep = "/api/steam" + ep
			}
		}

		resp, err := http.Post("http://127.0.0.1:8787"+ep, "application/json", strings.NewReader(payloadStr))
		if err != nil {
			res, _ := json.Marshal(map[string]interface{}{"ok": false, "error": err.Error()})
			return string(res)
		}
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		return string(body)
	})

	w.Bind("goTrimMemory", func() {
		trimMemory()
	})

	// 7. Инжекция полифила для 100% совместимости с ui/index.html
	polyfillJS := `
		window.pywebview = {
			api: {
				log: (l, t, m) => window.goLog(l, t, m),
				open_log_dir: () => window.goOpenLogDir(),
				get_log_content: () => window.goGetLogContent(),
				get_app_version: () => window.goGetAppVersion(),
				get_config: () => window.goGetConfig().then(res => {
					try { return typeof res === 'string' ? JSON.parse(res) : res; } catch(e) { return {}; }
				}),
				save_config: (cfg) => window.goSaveConfig(typeof cfg === 'string' ? cfg : JSON.stringify(cfg)),
				show_notification: (title, msg) => window.goShowNotification(title, msg),
				update_presence: (d, s, ps, pm, rc, gp) => window.goUpdatePresence(d, s, ps || 0, pm || 16, rc || '', gp || ''),
				update_tray: (s, ip) => window.goUpdateTray(s, ip),
				steam_get_status: () => window.goSteamGetStatus().then(res => {
					try { return typeof res === 'string' ? JSON.parse(res) : res; } catch(e) { return { steamRunning: false, tunnelActive: false }; }
				}),
				steam_start: () => window.goSteamStart().then(res => {
					try { return typeof res === 'string' ? JSON.parse(res) : res; } catch(e) { return { ok: false, error: String(e) }; }
				}),
				steam_stop: () => window.goSteamStop().then(res => {
					try { return typeof res === 'string' ? JSON.parse(res) : res; } catch(e) { return { ok: false, error: String(e) }; }
				}),
				steam_api: (ep, p) => window.goSteamApi(ep, JSON.stringify(p || {})).then(res => {
					try { return typeof res === 'string' ? JSON.parse(res) : res; } catch(e) { return { ok: false, error: String(e) }; }
				}),
				trim_memory: () => window.goTrimMemory()
			}
		};
		window.dispatchEvent(new Event("pywebviewready"));
	`
	w.Init(polyfillJS)

	// 8. Переход на страницу приложения
	w.Navigate("http://127.0.0.1:8787/")

	// 9. Автоматический фоновый тримминг памяти
	go func() {
		// Первичный сброс памяти после загрузки UI
		time.Sleep(2500 * time.Millisecond)
		trimMemory()
		logMessage("INFO", "Memory", "Initial startup working set trim applied")

		// Периодический сброс каждые 60 секунд
		ticker := time.NewTicker(60 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			trimMemory()
		}
	}()

	logMessage("INFO", "App", "Running Pure Go WebView2 loop")
	w.Run()

	// Завершение работы
	logMessage("INFO", "App", "Application exited cleanly")
	os.Exit(0)
}
