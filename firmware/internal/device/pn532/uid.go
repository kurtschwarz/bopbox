package pn532

const hexChars = "0123456789ABCDEF"

// UID represents an NFC tag unique identifier.
//
// UID is a fixed-size value type that can be freely copied, compared, and
// stored without heap allocation. Its String method returns colon-separated
// uppercase hex (e.g. "04:A3:2B:1C").
type UID struct {
	data [MaxUIDLen]byte
	len  byte
}

// NewUID creates a UID from a byte slice. Bytes beyond [MaxUIDLen] are silently
// truncated.
func NewUID(b []byte) UID {
	var u UID
	u.len = byte(copy(u.data[:], b))
	return u
}

// Bytes returns the raw UID bytes as a slice. The returned slice references
// the UID's internal array and must not be modified.
func (u UID) Bytes() []byte {
	return u.data[:u.len]
}

// Len returns the UID length in bytes.
func (u UID) Len() int {
	return int(u.len)
}

// IsZero reports whether the UID is empty (zero length).
func (u UID) IsZero() bool {
	return u.len == 0
}

// Equal reports whether two UIDs are identical in both length and content.
func (u UID) Equal(other UID) bool {
	if u.len != other.len {
		return false
	}

	for i := byte(0); i < u.len; i++ {
		if u.data[i] != other.data[i] {
			return false
		}
	}

	return true
}

// String returns the UID as colon-separated uppercase hex (e.g. "04:A3:2B:1C").
// Returns an empty string for a zero-length UID.
func (u UID) String() string {
	if u.len == 0 {
		return ""
	}

	buf := make([]byte, u.len*3-1)
	for i := byte(0); i < u.len; i++ {
		if i > 0 {
			buf[i*3-1] = ':'
		}

		buf[i*3] = hexChars[u.data[i]>>4]
		buf[i*3+1] = hexChars[u.data[i]&0x0F]
	}

	return string(buf)
}
