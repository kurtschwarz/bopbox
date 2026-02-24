package pn532

import "errors"

var (
	ErrTimeout    = errors.New("pn532: timeout")
	ErrBadLCS     = errors.New("pn532: bad length checksum")
	ErrBadDCS     = errors.New("pn532: bad data checksum")
	ErrBadTFI     = errors.New("pn532: bad TFI byte")
	ErrEmptyFrame = errors.New("pn532: empty frame")
	ErrFrameSize  = errors.New("pn532: frame too large")
	ErrWriteFail  = errors.New("pn532: UART write failed")
	ErrNoTag      = errors.New("pn532: no tag detected")
)
