#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
export FLASK_APP=rass.py
export FLASK_DEBUG=1
export RASS_DATAFOLDER=$DIR/data
python -m flask run --host=0.0.0.0
