package watchdog

import (
	"log/slog"
	"sync"
	"time"

	"machine"

	"bopbox/internal/service"
)

var _ service.Service = (*Service)(nil)

type Config struct {
	TimeoutMs uint32
	Interval  time.Duration
}

var DefaultConfig = Config{
	TimeoutMs: 5000,
	Interval:  500 * time.Millisecond,
}

type Service struct {
	service.Base

	log    *slog.Logger
	config Config
}

func New(config Config) *Service {
	return &Service{
		Base:   *service.New("watchdog"),
		log:    slog.Default().With("service", "watchdog"),
		config: config,
	}
}

func (s *Service) Start(wg *sync.WaitGroup) error {
	s.log.Info("starting")

	if s.State() == service.Running {
		s.log.Error("unable to start service, service already in running state")
		return service.ErrAlreadyRunning
	}

	s.SetState(service.Starting)

	machine.Watchdog.Configure(
		machine.WatchdogConfig{
			TimeoutMillis: s.config.TimeoutMs,
		},
	)

	machine.Watchdog.Start()

	wg.Add(1)
	go s.run(wg)

	s.log.Info("started")
	return nil
}

func (s *Service) Stop() error {
	s.log.Info("stopping")

	if s.State() == service.Stopped {
		s.log.Error("unable to stop service, service is not running")
		return service.ErrNotRunning
	}

	s.SetState(service.Stopping)
	s.SetState(service.Stopped)

	s.log.Info("stopped")
	return nil
}

func (s *Service) run(wg *sync.WaitGroup) error {
	s.log.Info("running")

	if s.State() == service.Running {
		s.log.Error("unable to run service, service is already running")
		return service.ErrAlreadyRunning
	}

	s.SetState(service.Running)

	defer wg.Done()
	defer func() {
		if r := recover(); r != nil {
			s.log.Error("panic recovered", "error", r)
		}
	}()

	for {
		machine.Watchdog.Update()
		time.Sleep(s.config.Interval)
	}
}
