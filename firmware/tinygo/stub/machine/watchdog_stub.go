package machine

type WatchdogConfig struct {
	TimeoutMillis uint32
}

type watchdog struct{}

func (w *watchdog) Configure(config WatchdogConfig) {}
func (w *watchdog) Start()                          {}
func (w *watchdog) Update()                         {}

var Watchdog = &watchdog{}
