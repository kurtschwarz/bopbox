package pn532

import "time"

// commands (§7).
const (
	cmdGetFirmwareVersion  = 0x02
	cmdSAMConfiguration    = 0x14
	cmdRFConfiguration     = 0x32
	cmdInListPassiveTarget = 0x4A
)

// command timeout
const DefaultCmdTimeout = 5 * time.Second

const MaxTagUIDLen = 10

// frame protocol constants (§6.2.1.1).
const (
	frameStartCode1  = 0x00
	frameStartCode2  = 0xFF
	framePostamble   = 0x00
	frameHostToPN532 = 0xD4
	framePN532ToHost = 0xD5
)

// frame types
const (
	frameTypeACK  = 0
	frameTypeNACK = 1
	frameTypeData = 2
)

// wakeup frame
var frameWakeUp = [16]byte{0x55, 0x55, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}
