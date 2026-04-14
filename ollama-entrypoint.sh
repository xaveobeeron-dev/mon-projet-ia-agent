#!/bin/sh
chmod +x /entrypoint.sh
ollama serve &
sleep 5
ollama pull phi3
ollama pull phi3-mini
wait
