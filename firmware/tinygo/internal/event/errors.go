package event

import "errors"

var ErrBusFull = errors.New("event: subscriber limit reached")
