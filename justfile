build-path := '.build'

mpy-cross := `which mpy-cross`
mpremote := `which mpremote`

run:
  #!/usr/bin/env bash
  set -exuo pipefail

  {{mpremote}} mount . run --no-follow main.py repl

build: (clean)
  #!/usr/bin/env bash
  set -exuo pipefail

  mkdir -p {{build-path}}
  find . -name '*.py' | xargs -P 0 -I {} sh -c 'mkdir -p "{{build-path}}/$(dirname "$1")" && mpy-cross -o "{{build-path}}/${1%.py}.mpy" "$1"' _ {}
  cp config.json {{build-path}}

clean:
  #!/usr/bin/env bash
  set -exuo pipefail

  rm -rf {{build-path}}

upload: (build)
  #!/usr/bin/env bash
  set -exuo pipefail

  {{mpremote}} cp -r {{build-path}}/* : + soft-reset
