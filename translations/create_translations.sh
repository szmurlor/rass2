#!/bin/bash
pybabel extract -F babel.cfg -o messages.pot .
pybabel init -i messages.pot -d translations -l pl
pybabel init -i messages.pot -d translations -l en