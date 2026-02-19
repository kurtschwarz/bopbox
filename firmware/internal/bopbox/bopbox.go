package bopbox

import (
	"log/slog"
	"machine"
	"time"
)

type Config struct {
	WatchdogTimeoutMs uint32
	WatchdogInterval  time.Duration
	LogLevel          slog.Level
}

var DefaultConfig = Config{
	WatchdogTimeoutMs: 5000,
	WatchdogInterval:  500 * time.Millisecond,
	LogLevel:          slog.LevelDebug,
}

type BopBox struct {
	config Config
	log    *slog.Logger
}

func New(config Config) *BopBox {
	return &BopBox{
		config: config,
		log:    slog.Default().With("component", "bopbox"),
	}
}

func (b *BopBox) Run() {
	b.log.Info("bopbox starting")
	b.startWatchdog()

	// for {
	// 	machine.Watchdog.Update()
	// }
}

func (b *BopBox) startWatchdog() {
	machine.Watchdog.Configure(
		machine.WatchdogConfig{
			TimeoutMillis: b.config.WatchdogTimeoutMs,
		},
	)

	machine.Watchdog.Start()

	b.log.Info("watchdog started", "timeout_ms", b.config.WatchdogTimeoutMs)
}
