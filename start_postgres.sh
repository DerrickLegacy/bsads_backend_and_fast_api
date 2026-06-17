#!/bin/bash
# Auto-detect PostgreSQL version and start it

PG_VERSION=$(ls /usr/lib/postgresql/ | head -n1)
PG_BIN=/usr/lib/postgresql/$PG_VERSION/bin
PG_DATA=/var/lib/postgresql/$PG_VERSION/main

echo "Starting PostgreSQL $PG_VERSION from $PG_DATA"
exec $PG_BIN/postgres -D $PG_DATA
