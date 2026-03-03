package main

import (
	"fmt"
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
	var startTime = time.Now()

	waitForSerial(5 * time.Second)

	slog.SetDefault(
		slog.New(
			tint.NewHandler(
				machine.Serial,
				&tint.Options{
					Level:      slog.LevelDebug,
					TimeFormat: time.Kitchen,
					ReplaceAttr: func(groups []string, a slog.Attr) slog.Attr {
						if a.Key == slog.TimeKey {
							elapsed := time.Since(startTime)
							mins := int(elapsed.Minutes())
							secs := elapsed.Seconds() - float64(mins*60)
							a.Value = slog.StringValue(fmt.Sprintf("%02d:%05.2f", mins, secs))
						}

						return a
					},
				}),
		),
	)

	bopbox := bopbox.New(bopbox.DefaultConfig)
	bopbox.Run()
}
