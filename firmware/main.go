package main

import (
	"log/slog"
	"machine"
	"time"

	"bopbox/internal/bopbox"

	"github.com/lmittmann/tint"
)

func waitForSerial(timeout time.Duration) bool {
	deadline := time.Now().Add(timeout)
	for !machine.Serial.DTR() {
		if time.Now().After(deadline) {
			return false
		}

		time.Sleep(10 * time.Millisecond)
	}

	return true
}

func main() {
	waitForSerial(2 * time.Second)

	slog.SetDefault(
		slog.New(
			tint.NewHandler(
				machine.Serial,
				&tint.Options{
					Level:      slog.LevelDebug,
					TimeFormat: time.Kitchen,
				}),
		),
	)

	bopbox := bopbox.New(bopbox.DefaultConfig)
	bopbox.Run()
}
