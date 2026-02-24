package nfc

import (
	"log/slog"
	"sync"
	"time"

	"machine"

	"bopbox/internal/device/pn532"
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
	device *pn532.Device

	lastTagUID    [pn532.MaxTagUIDLen]byte
	lastTagUIDLen int
}

func New(
	config Config,
) *Service {
	return &Service{
		Base:   *service.New("nfc"),
		log:    slog.Default().With("service", "nfc"),
		config: config,
		device: nil,
	}
}

func (s *Service) Start(
	wg *sync.WaitGroup,
) error {
	s.log.Info("starting")

	machine.UART0.Configure(
		machine.UARTConfig{
			TX:       machine.GPIO0,
			RX:       machine.GPIO1,
			BaudRate: 115200,
		},
	)

	s.device = pn532.New(pn532.DefaultConfig, machine.UART0)
	s.device.Init()

	wg.Add(1)
	go s.run(wg)

	s.log.Info("started")

	return nil
}

func (s *Service) Stop() error {
	s.log.Info("stopping")
	return nil
}

func (s *Service) run(
	wg *sync.WaitGroup,
) error {
	s.log.Info("running")

	defer wg.Done()
	defer func() {
		if r := recover(); r != nil {
			s.log.Error("panic recovered", "error", r)
		}
	}()

	for {
		uid, err := s.device.ReadTag()
		if err != nil {
			if err != pn532.ErrNoTag {
				s.log.Error("read failed", "error", err.Error())
			}

			s.clearLastTagUID()
			continue
		}

		if uid != nil {
			if s.isSameTagUID(uid) {
				continue
			}

			s.log.Info("tag detected", "uid", uid)
			s.setLastTagUID(uid)
		}

		time.Sleep(s.config.Interval)
	}
}

func (s *Service) isSameTagUID(uid []byte) bool {
	if len(uid) != s.lastTagUIDLen {
		return false
	}

	for i := 0; i < s.lastTagUIDLen; i++ {
		if s.lastTagUID[i] != uid[i] {
			return false
		}
	}

	return true
}
func (s *Service) setLastTagUID(uid []byte) {
	s.lastTagUIDLen = copy(s.lastTagUID[:], uid)
}

func (s *Service) clearLastTagUID() {
	s.lastTagUIDLen = 0
}
