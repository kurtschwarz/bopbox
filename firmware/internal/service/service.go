package service

import (
	"errors"
	"sync"
)

type State int

const (
	Stopped State = iota
	Starting
	Running
	Stopping
	Errored
)

var ErrAlreadyRunning = errors.New("service already running")
var ErrNotRunning = errors.New("service not running")

type Service interface {
	Name() string
	Start(wg *sync.WaitGroup) error
	Stop() error
	State() State
}

type Base struct {
	name  string
	state State
}

func (b *Base) Name() string     { return b.name }
func (b *Base) SetName(n string) { b.name = n }

func (b *Base) State() State     { return b.state }
func (b *Base) SetState(s State) { b.state = s }

func New(name string) *Base {
	return &Base{
		name:  name,
		state: Stopped,
	}
}
