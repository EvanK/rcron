#!/usr/bin/env python2

import sys
import syslog
import time
import os.path
import getopt
import ConfigParser
import inspect

class Rcron:
    # version number
    VERSION = '0.2.0'

    # default file paths
    DEF_CONF_FILE = '/etc/rcron/rcron.conf'
    DEF_STATE_FILES = ['/var/run/rcron.state', '/var/run/rcron/state'] # support rcron/state for bc

    # shared configuration
    config = None

    # get basename with which to refer to ourself
    progname = os.path.basename(sys.argv[0])

    # cmd line opts to support
    optlist, args = getopt.getopt(sys.argv[1:], '', ['help', 'version', 'generate', 'conf='])

    def __init__(self):
        # handle generic opts first
        for opt, arg in self.optlist:
            if opt == '--help':
                self.usage()
            if opt == '--version':
                print "rcron %s" % self.VERSION
                sys.exit(0)

        # attempt loading config & opening syslog
        self.load_config()
        self.open_syslog()

        # handle any other complex opts
        for opt, arg in self.optlist:
            if opt == '--generate':
                try:
                    f = open(self.config.get('default','state_file'), 'w')
                    f.write(self.config.get('default', 'default_state'))
                    f.close()
                    self.write_syslog('cluster=%s state=%s status=generate file=%s' % (self.config.get('default', 'cluster_name'), self.config.get('default', 'default_state'), self.config.get('default', 'state_file')))
                    sys.exit(0)
                except IOError, e:
                    self.warn("failed to generate state file '%s' : %s" % (self.config.get('default', 'state_file'), e.strerror))
                    sys.exit(1)

        if len(self.args) < 1:
            self.usage('not enough arguments')

        current_state = self.get_state()

        if current_state == 'passive':
            self.write_syslog("cluster=%s state=passive status=ignore cmd=%s" % (self.config.get('default', 'cluster_name'), ' '.join(self.args)))
            sys.exit(0)

        start = time.clock()
        self.write_syslog("cluster=%s state=active status=start cmd=%s" % (self.config.get('default', 'cluster_name'), ' '.join(self.args)))

        rc = os.system("nice -n %s %s" % (self.config.get('default', 'nice_level'), ' '.join(self.args)))

        runtime = start - time.clock()

        self.write_syslog("cluster=%s state=active status=%s dur=%i cmd=%s" % (self.config.get('default', 'cluster_name'), 'ok' if rc == 0 else 'fail', runtime, ' '.join(self.args)))

        sys.exit(0)

    def get_state(self):
        if self.config.get('default', 'state_file') == self.DEF_STATE_FILES[0]:
            (state, err) = self.slurp_file(self.DEF_STATE_FILES[0])
            if state is None:
                (state, err2) = self.slurp_file(self.DEF_STATE_FILES[1])
                if state is not None:
                    self.config.get('default', 'state_file') == self.DEF_STATE_FILES[1]
            if state is None:
                self.warn("failed to read state file '%s' : %s" % (self.config.get('default', 'state_file'), err))
                sys.exit(1)
        else:
            (state, err) = self.slurp_file(self.config.get('default', 'state_file'))
            if state is None:
                self.warn("failed to read state file '%s' : %s" % (self.config.get('default', 'state_file'), err))
                sys.exit(1)

        if state not in ('active', 'passive'):
            self.warn("corrupted state file '%s' (content='%s'), using default state (%s)" % (self.config.get('default', 'state_file'), state, self.config.get('default', 'default_state')))
            state = self.config.get('default', 'default_state')

        return state

    def slurp_file(self, path):
        try:
            f = open(path)
            content = f.read()
            f.close()
            return [content.strip(), None]
        except IOError, e:
            return [None, e.strerror]

    def load_config(self):
        conf_file = self.DEF_CONF_FILE

        for opt, arg in self.optlist:
            if opt == '--conf':
                conf_file=arg
                break

        try:
            config = ConfigParser.RawConfigParser({
                'cluster_name': 'default_cluster',
                'state_file': self.DEF_STATE_FILES[0],
                'default_state': 'active',
                'syslog_facility': 'LOG_CRON',
                'syslog_level': 'LOG_INFO',
                'nice_level': '19'
            })
            config.readfp(FakeSecHead(open(conf_file)))

            self.config = config
        except ConfigParser.Error, e:
            self.warn("couldn't open config: %s" % e)
            sys.exit(1)
        except IOError, e:
            self.warn("failed to open config file '%s' : %s" % (conf_file, e.strerror))
            sys.exit(1)

    def open_syslog(self):
        if not hasattr(syslog, self.config.get('default', 'syslog_facility')):
            self.warn('bad syslog_facility: %s' % self.config.get('default', 'syslog_facility'))
        if not hasattr(syslog, self.config.get('default', 'syslog_level')):
            self.warn('bad syslog_level: %s' % self.config.get('default', 'syslog_level'))

        syslog.openlog(self.progname, syslog.LOG_PID | syslog.LOG_NDELAY, getattr(syslog, self.config.get('default', 'syslog_facility')))

    def write_syslog(self, message):
        syslog.syslog(getattr(syslog, self.config.get('default', 'syslog_level')), message)

    def warn(self, message):
        callerframerecord = inspect.stack()[1]
        frame = callerframerecord[0]
        info = inspect.getframeinfo(frame)

        warning = "%s (%s:%d, %s) warning: %s" % (self.progname, info.filename, info.lineno, info.function, message)

        print >> sys.stderr, warning
        syslog.syslog(syslog.LOG_INFO, warning)

    def usage(self, message=None):
        if message:
            print >> sys.stderr, "%s\n" % message

        print >> sys.stderr, "Usage:\n%s [--help] [--version] [--generate] [--conf file] command [args]\n" % self.progname
        sys.exit(1)

class FakeSecHead(object):
    def __init__(self, fp):
        self.fp = fp
        self.sechead = '[default]\n'

    def readline(self):
        if self.sechead:
            try:
                return self.sechead
            finally:
                self.sechead = None
        else:
            return self.fp.readline()

if __name__ == '__main__':
    Rcron()
