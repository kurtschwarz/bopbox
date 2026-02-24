package bopbox

import (
	"log/slog"
	"sync"
	"time"

	"bopbox/internal/event"
	"bopbox/internal/service"
	"bopbox/internal/service/nfc"
	"bopbox/internal/service/watchdog"
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
	config   Config
	log      *slog.Logger
	events   *event.EventBus
	services *Services
}

type Services struct {
	watchdog *watchdog.Service
	nfc      *nfc.Service
}

func (s *Services) All() []service.Service {
	return []service.Service{
		s.watchdog,
		s.nfc,
	}
}

func New(config Config) *BopBox {
	events := event.NewBus()

	return &BopBox{
		log:    slog.Default().With("service", "bopbox"),
		config: config,
		events: events,
		services: &Services{
			watchdog: watchdog.New(watchdog.DefaultConfig),
			nfc:      nfc.New(nfc.DefaultConfig, events),
		},
	}
}

func (b *BopBox) Run() {
	b.log.Info("running")

	wg := sync.WaitGroup{}
	for _, svc := range b.services.All() {
		if err := svc.Start(&wg); err != nil {
			b.log.Error("failed to start service", "name", svc.Name())
		}
	}

	wg.Wait()
}
