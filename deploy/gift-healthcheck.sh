#!/bin/bash
# The Gift healthcheck — runs every 5 minutes via rnk's crontab on atlas.
#
# Checks https://gift.rnkstudios.uk/healthz (the door a visitor actually uses,
# so it catches service, tunnel, DNS, and edge failures alike). Emails on the
# transition into failure, reminds hourly while still down, emails once on
# recovery. Log: /home/rnk/gift-health.log
#
# Override the target for testing:  GIFT_HEALTH_URL=http://127.0.0.1:9999 ./gift-healthcheck.sh

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
URL="${GIFT_HEALTH_URL:-https://gift.rnkstudios.uk/healthz}"
EMAIL="${GIFT_HEALTH_EMAIL:-bd@rnk-enterprise.us}"
FROM="gift@rnkstudios.uk"
STATE="${GIFT_HEALTH_STATE:-/home/rnk/.gift-health.state}"
LOG="${GIFT_HEALTH_LOG:-/home/rnk/gift-health.log}"
SENDMAIL="${GIFT_HEALTH_SENDMAIL:-sendmail}"

NOW=$(date +%s)
STAMP=$(date "+%Y-%m-%d %H:%M:%S")

send_alert() {  # $1 = subject, $2 = body
    if ! command -v "${SENDMAIL%% *}" >/dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: mailer '$SENDMAIL' not found — alert NOT sent: $1" >> "$LOG"
        return 1
    fi
    ${SENDMAIL} -t <<EOF
From: The Gift <${FROM}>
To: ${EMAIL}
Subject: ${1}
Content-Type: text/plain; charset=utf-8

${2}

-- 
gift-healthcheck on atlas ($(hostname))
EOF
}

diagnose() {
    echo "Triage:"
    echo "  systemd unit : $(systemctl is-active the-gift 2>&1)"
    echo "  local :8770   : $(curl -fsS -m 5 http://127.0.0.1:8770/healthz 2>/dev/null || echo 'no answer')"
    echo "  pm2 tunnel    : $(pm2 pid rnkstudios-web-tunnel 2>/dev/null | grep -q '[0-9]' && echo running || echo 'not running')"
}

if curl -fsS -m 15 "$URL" 2>/dev/null | grep -q '"ok"'; then
    if [ -f "$STATE" ]; then
        DOWN_SINCE=$(cat "$STATE" 2>/dev/null || echo "$NOW")
        MINS=$(( (NOW - DOWN_SINCE) / 60 ))
        rm -f "$STATE"
        echo "[$STAMP] recovered after ${MINS} min" >> "$LOG"
        send_alert "[OK] gift.rnkstudios.uk recovered" \
"The Gift answered /healthz again after ${MINS} minute(s) of downtime.
$(diagnose)"
    else
        echo "[$STAMP] ok" >> "$LOG"
    fi
    exit 0
fi

# unhealthy
if [ -f "$STATE" ]; then
    DOWN_SINCE=$(cat "$STATE" 2>/dev/null || echo "$NOW")
    MINS=$(( (NOW - DOWN_SINCE) / 60 ))
    echo "[$STAMP] still down (${MINS} min)" >> "$LOG"
    # re-alert on the hour mark (50-55..59+ window so one cron tick per hour fires)
    if [ $(( MINS % 60 )) -ge 55 ] || [ $(( MINS % 60 )) -le 4 ]; then
        send_alert "[DOWN] gift.rnkstudios.uk still down (${MINS} min)" \
"The Gift is still not answering /healthz (down ~${MINS} min).
$(diagnose)"
    fi
else
    echo "$NOW" > "$STATE"
    echo "[$STAMP] DOWN — alerting $EMAIL" >> "$LOG"
    send_alert "[DOWN] gift.rnkstudios.uk is not answering" \
"The Gift failed its healthcheck: $URL did not return {\"ok\": true}.
$(diagnose)"
fi
