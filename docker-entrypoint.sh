#!/bin/sh

CURRENT_UID=$(id -u appuser)
CURRENT_GID=$(id -g appuser)

CURRENT_HOME=$(getent passwd appuser | cut -d ":" -f6)

DATA_UID=$(stat -c %u /data 2>/dev/null)
DATA_GID=$(stat -c %g /data 2>/dev/null)

PUID=${PUID:-${DATA_UID:-1000}}
PGID=${PGID:-${DATA_GID:-1000}}

# Exit if root user
if [ "${PUID}" = "0" ] || [ "${PGID}" = "0" ]; then
    echo "Error: Running as root is not supported. Please set PUID and PGID to non-root values."
    exit 1
fi

# Update group if needed
if [ "${CURRENT_GID}" != "${PGID}" ]; then
    groupmod -o -g "${PGID}" appuser
fi

# Update user if needed
if [ "${CURRENT_UID}" != "${PUID}" ]; then
    usermod -o -u "${PUID}" appuser
fi

# Fix ownership of home directory if needed
if [ -d "${CURRENT_HOME}" ] && \
   [ "$(stat -c %u:%g "${CURRENT_HOME}" 2>/dev/null)" != "${PUID}:${PGID}" ]; then
    chown -R appuser:appuser /home/appuser
fi

# Fix ownership of /data if needed (non-recursive)
if [ -d /data ] && \
   [ "$(stat -c %u:%g /data 2>/dev/null)" != "${PUID}:${PGID}" ]; then
    chown appuser:appuser /data
fi

# Launch the app as appuser
exec su-exec appuser \
    python craigslist-renew.py /data/config.yml "$@"
