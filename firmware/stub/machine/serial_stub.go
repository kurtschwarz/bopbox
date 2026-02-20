//go:build !tinygo

package machine

import "os"

type serial struct{}

func (s *serial) Configure() error               { return nil }
func (s *serial) Write(data []byte) (int, error) { return os.Stdout.Write(data) }
func (s *serial) Read(data []byte) (int, error)  { return 0, nil }
func (s *serial) DTR() bool                      { return true }

var Serial = &serial{}
