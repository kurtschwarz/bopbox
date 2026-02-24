package pn532

import "io"

// Transporter abstracts the byte-level transport (UART, SPI, etc.).
// io.ReadWriter handles data transfer; Buffered reports bytes available
// without blocking, enabling non-blocking poll loops.
type Transporter interface {
	io.ReadWriter

	Buffered() int
}
