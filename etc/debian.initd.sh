#!/bin/sh

### BEGIN INIT INFO
# Provides:          rcron
# Required-Start:    $remote_fs $syslog
# Default-Start:     2 3 4 5
# Short-Description: Ensure rcron is ready to run
### END INIT INFO

PATH=/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=/bin/rcron
NAME=rcron
DESC="redundant cron middleware"
CONFIG=/etc/rcron/rcron.conf

#includes lsb functions
. /lib/lsb/init-functions

#includes service defaults, if any
[ -r /etc/default/rcron ] && . /etc/default/rcron

test -f $CONFIG || exit 0
test -f $DAEMON || exit 0

case "$1" in
    start|restart|reload|force-reload)
        log_daemon_msg "Bootstrapping $DESC" "$NAME"
        $DAEMON --conf=$CONFIG --generate > /dev/null 2>&1

        if [ $? -eq 0 ]; then
            log_end_msg 0
        else
            log_end_msg 1
        fi
        ;;
    stop)
        log_daemon_msg "No-op $DESC" "$NAME"
        log_end_msg 0
        ;;
    *)
       echo "Usage: /etc/init.d/$NAME {start|stop|restart|reload|force-reload}" >&2
       exit 1
        ;;
esac

exit 0
