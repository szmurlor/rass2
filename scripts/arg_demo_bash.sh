#!/bin/bash
argc=$#
argv=("$@")

for (( i=0; i<argc; i++ )); do
	echo "${argv[i]}"
done
