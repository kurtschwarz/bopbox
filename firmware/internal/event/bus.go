package event

import "sync"

// subscriber holds a single subscription registration, pairing a channel
// with a bitmask indicating which event types should be delivered to it.
type subscriber struct {
	mask uint32     // bitmask of EventTypes this subscriber cares about
	ch   chan Event // destination channel for matched events
}

// EventBus is a lightweight, zero-allocation publish/subscribe dispatcher.
// Services subscribe with a channel and a set of event types they care about,
// and publishers broadcast events without knowledge of the listeners.
//
// EventBus supports up to 8 concurrent subscribers and up to 32 distinct
// event types (limited by the uint32 bitmask). It is safe for concurrent use:
// multiple goroutines may publish simultaneously, and subscriptions may be
// added while publishing is active.
type EventBus struct {
	mu   sync.RWMutex
	subs [8]subscriber // fixed capacity, no map/slice growth
	n    int
}

// NewBus creates a ready-to-use [EventBus].
func NewBus() *EventBus {
	return &EventBus{}
}

// Subscribe registers ch to receive events matching any of the given types.
// The caller owns the channel and is responsible for draining it. Returns
// [ErrBusFull] if the maximum subscriber count has been reached.
func (b *EventBus) Subscribe(
	ch chan Event,
	types ...EventType,
) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.n >= len(b.subs) {
		return ErrBusFull
	}

	var mask uint32
	for _, t := range types {
		mask |= 1 << t
	}

	b.subs[b.n] = subscriber{mask: mask, ch: ch}
	b.n++
	return nil
}

// Publish delivers e to every subscriber whose type mask matches e.Type.
// Delivery is non-blocking: if a subscriber's channel is full, the event
// is dropped for that subscriber to prevent a stalled consumer from blocking
// the publisher. Callers should size subscriber channels to tolerate
// transient bursts.
//
// Publish is safe to call concurrently from multiple goroutines.
func (b *EventBus) Publish(
	e Event,
) {
	b.mu.RLock()
	n := b.n
	b.mu.RUnlock()

	for i := 0; i < n; i++ {
		if b.subs[i].mask&(1<<e.Type) != 0 {
			select {
			case b.subs[i].ch <- e:
			default:
				// TODO: log dropped event
			}
		}
	}
}
