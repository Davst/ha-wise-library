#!/bin/sh
set -eu
mkdir -p /data/session
chown -R library:library /data/session
chmod 700 /data/session
# Supervisor options are root-owned; copy only for the non-root process.
cp /data/options.json /data/session/options.json
chown library:library /data/session/options.json
chmod 600 /data/session/options.json
export WISE_OPTIONS=/data/session/options.json
export WISE_DATA=/data/session
exec su -s /bin/sh library -c 'exec python -m app.server'
