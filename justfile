docker  := `which docker`
micropython := docker + ' run -ti -v ./:/workspace -w /workspace --rm micropython/unix:v1.26.0@sha256:5c45d10073e2ee300ca1d4c50ba9895e7748e383657271b0d1ad15e2b6ab9d06 micropython'

run:
  {{micropython}} main.py
