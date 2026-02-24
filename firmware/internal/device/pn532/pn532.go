package pn532

import (
	"errors"
	"time"
)

type FirmwareVersion struct {
	IC       byte
	Version  byte
	Revision byte
	Support  byte
}

type Config struct{}

var DefaultConfig = Config{}

// Device communicates with a PN532 over a Transporter
type Device struct {
	config    Config
	transport Transporter
	reader    Reader

	cmdBuf [64]byte // outgoing command frame buffer
}

// New creates a PN532 driver. The Transporter must already be configured
// (baud rate, pins, etc.) before calling New.
func New(config Config, transport Transporter) *Device {
	return &Device{
		config:    config,
		transport: transport,
		reader: Reader{
			transport: transport,
		},
	}
}

func (d *Device) Init() {
	d.wake()
}

func (d *Device) SAMConfig(mode byte) error {
	_, err := d.sendCommand(cmdSAMConfiguration, []byte{mode, 0x14, 0x01})
	return err
}

func (d *Device) GetFirmwareVersion() (FirmwareVersion, error) {
	f, err := d.sendCommand(cmdGetFirmwareVersion, nil)
	if err != nil {
		return FirmwareVersion{}, err
	}

	if len(f.data) < 4 {
		return FirmwareVersion{}, ErrEmptyFrame
	}

	return FirmwareVersion{
		IC:       f.data[0],
		Version:  f.data[1],
		Revision: f.data[2],
		Support:  f.data[3],
	}, nil
}

func (d *Device) ReadTag() ([]byte, error) {
	f, err := d.sendCommand(cmdInListPassiveTarget, []byte{0x01, 0x00})
	if err != nil {
		return nil, err
	}

	// data[0] = number of targets found
	if len(f.data) == 0 || f.data[0] == 0x00 {
		return nil, ErrNoTag
	}

	// data[5] = UID length, data[6:6+uidLen] = UID
	if len(f.data) < 6 {
		return nil, ErrEmptyFrame
	}

	uidLen := int(f.data[5])
	if len(f.data) < 6+uidLen {
		return nil, ErrEmptyFrame
	}

	// Return a copy so our buffer can be reused.
	uid := make([]byte, uidLen)
	copy(uid, f.data[6:6+uidLen])

	return uid, nil
}

func (d *Device) sendCommand(
	command byte,
	data []byte,
) (*frame, error) {
	d.wake()

	// Build and send the command frame
	n := d.buildCommandFrame(command, data)
	if err := d.write(d.cmdBuf[:n]); err != nil {
		return nil, err
	}

	// Wait for ACK
	f, err := d.reader.read(DefaultCmdTimeout)
	if err != nil {
		return nil, err
	}

	if f.typ != frameTypeACK {
		return nil, errors.New("pn532: expected ACK, got different frame")
	}

	// Wait for data response
	f, err = d.reader.read(DefaultCmdTimeout)
	if err != nil {
		return nil, err
	}

	if f.typ != frameTypeData {
		return nil, errors.New("pn532: expected data frame")
	}

	return f, nil
}

func (d *Device) buildCommandFrame(command byte, data []byte) int {
	dataLen := len(data)
	length := byte(dataLen + 2)              // TFI + command + data
	lcs := byte((^uint8(length) + 1) & 0xFF) // length checksum

	buf := d.cmdBuf[:]
	buf[0] = 0x00 // preamble
	buf[1] = frameStartCode1
	buf[2] = frameStartCode2
	buf[3] = length
	buf[4] = lcs
	buf[5] = frameHostToPN532
	buf[6] = command

	dcsSum := uint16(frameHostToPN532) + uint16(command)
	for i := 0; i < dataLen; i++ {
		buf[7+i] = data[i]
		dcsSum += uint16(data[i])
	}

	buf[7+dataLen] = byte((^uint8(dcsSum) + 1) & 0xFF) // data checksum
	buf[8+dataLen] = framePostamble

	return 9 + dataLen
}

func (d *Device) wake() {
	d.write(frameWakeUp[:])
	time.Sleep(1 * time.Millisecond)
}

func (d *Device) write(data []byte) error {
	n, err := d.transport.Write(data)
	if err != nil {
		return err
	}

	if n < len(data) {
		return ErrWriteFail
	}

	return nil
}
