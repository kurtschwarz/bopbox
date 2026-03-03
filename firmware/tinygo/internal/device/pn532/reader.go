package pn532

import (
	"time"
)

// frame represents a parsed PN532 response frame
type frame struct {
	typ     int
	command byte
	data    []byte
}

const (
	stateIdle = iota
	stateStart1
	stateLen
	stateLCS
	stateBody
	stateDCS
	statePostamble
)

type Reader struct {
	transport Transporter

	rxBuf   [64]byte // UART read buffer
	bodyBuf [64]byte // frame body accumulator

	// Bytes read from UART but not yet consumed by the frame parser.
	// This happens when a single Read() returns bytes spanning multiple
	// frames (e.g. ACK + data frame back to back).
	pending    [128]byte
	pendingLen int
}

func (r *Reader) read(timeout time.Duration) (*frame, error) {
	deadline := time.Now().Add(timeout)

	state := stateIdle
	var bodyPos int
	var frameLen int
	var frameLCS int

	// processBytes runs bytes through the state machine. On a complete frame,
	// it saves any unprocessed remainder into r.pending and returns the frame.
	processBytes := func(buf []byte, n int) *frame {
		for i := 0; i < n; i++ {
			b := buf[i]

			switch state {
			case stateIdle:
				if b == frameStartCode1 {
					state = stateStart1
				}

			case stateStart1:
				if b == frameStartCode2 {
					state = stateLen
				} else if b != frameStartCode1 {
					state = stateIdle
				}

			case stateLen:
				frameLen = int(b)
				state = stateLCS

			case stateLCS:
				frameLCS = int(b)

				switch {
				case frameLen == 0x00 && frameLCS == 0xFF:
					// ACK — save remaining bytes for next call.
					r.pendingLen = copy(r.pending[:], buf[i+1:n])
					return &frame{typ: frameTypeACK}

				case frameLen == 0xFF && frameLCS == 0x00:
					r.pendingLen = copy(r.pending[:], buf[i+1:n])
					return &frame{typ: frameTypeNACK}

				case (frameLen+frameLCS)&0xFF != 0:
					state = stateIdle // recoverable — skip bad frame

				case frameLen < 1:
					state = stateIdle

				case frameLen > len(r.bodyBuf):
					state = stateIdle

				default:
					bodyPos = 0
					state = stateBody
				}

			case stateBody:
				r.bodyBuf[bodyPos] = b
				bodyPos++
				if bodyPos >= frameLen {
					state = stateDCS
				}

			case stateDCS:
				var dcsSum int
				for j := 0; j < frameLen; j++ {
					dcsSum += int(r.bodyBuf[j])
				}
				dcsSum += int(b)
				if dcsSum&0xFF != 0 {
					state = stateIdle // recoverable
				} else {
					state = statePostamble
				}

			case statePostamble:
				if r.bodyBuf[0] != framePN532ToHost {
					state = stateIdle
					continue
				}

				// Save remainder for next call.
				r.pendingLen = copy(r.pending[:], buf[i+1:n])

				bodyData := make([]byte, frameLen-2)
				copy(bodyData, r.bodyBuf[2:frameLen])

				return &frame{
					typ:     frameTypeData,
					command: r.bodyBuf[1],
					data:    bodyData,
				}
			}
		}
		return nil
	}

	// First, drain any bytes left over from the previous readFrame call.
	if r.pendingLen > 0 {
		n := r.pendingLen
		r.pendingLen = 0
		if f := processBytes(r.pending[:n], n); f != nil {
			return f, nil
		}
	}

	for {
		if time.Now().After(deadline) {
			return nil, ErrTimeout
		}

		if r.transport.Buffered() == 0 {
			time.Sleep(1 * time.Millisecond)
			continue
		}

		n, err := r.transport.Read(r.rxBuf[:])
		if err != nil {
			return nil, err
		}

		if f := processBytes(r.rxBuf[:n], n); f != nil {
			return f, nil
		}
	}
}
