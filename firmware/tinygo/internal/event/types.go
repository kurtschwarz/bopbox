package event

type EventType uint8

const (
	EventTagDetected EventType = iota
	EventTagRemoved
)

type Event struct {
	Type    EventType
	Payload [32]byte // fixed-size, avoids heap allocation
}

func NewEvent(t EventType, data []byte) Event {
	e := Event{Type: t}
	copy(e.Payload[:], data)
	return e
}
