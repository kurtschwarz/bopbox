tinygo := `which tinygo`

[working-directory: './firmware']
dev:
  #!/usr/bin/env bash
  set -exuo pipefail

  go run -modfile go.local.mod .

[working-directory: './firmware']
run:
  #!/usr/bin/env bash
  set -exuo pipefail

  {{tinygo}} flash -target=pico2 -monitor .

[working-directory: './firmware']
flash:
  #!/usr/bin/env bash
  set -exuo pipefail

  {{tinygo}} flash -target=pico2 .
