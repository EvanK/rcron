#!/usr/bin/env python2

import unittest
import sys
import subprocess
import os.path

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.cwd = os.path.dirname(os.path.abspath(__file__))
        self.progname = self.cwd+'/../src/rcron.py'
        self.progversion = '0.2.0'
        self.statepath = '/tmp/rcron.state'
        self.usage = "Usage:\nrcron.py [--help] [--version] [--generate] [--conf file] command [args]"

    def test_version(self):
        output = self._run_with(['--version'])
        self.assertEqual('rcron %s' % self.progversion, output)

    def test_help(self):
        output = self._except_with(['--help'])
        self.assertEqual(self.usage, output.strip())

    def test_generate(self):
        if os.path.isfile(self.statepath):
            os.remove(self.statepath)

        self._generate_with_conf('passive')

        if not os.path.isfile(self.statepath):
            self.fail('Should have created state file at %s' % self.statepath)

        f = open(self.statepath)
        statecontent = f.read()
        f.close()
        self.assertEqual('passive', statecontent.strip())

    def test_run_passive(self):
        self._generate_with_conf('passive')

        output = self._run_with(['--conf', self.cwd+'/passive.conf', 'echo', 'foo'])
        self.assertEqual('', output.strip())

    def test_run_active(self):
        self._generate_with_conf('active')

        output = self._run_with(['--conf', self.cwd+'/active.conf', 'echo', 'foo'])
        self.assertEqual('foo', output.strip())

    def test_run_noargs(self):
        self._generate_with_conf('passive')

        output = self._except_with(['--conf', self.cwd+'/passive.conf'])
        self.assertEqual("not enough arguments\n\n"+self.usage, output)

    def test_bad_config(self):
        output = self._except_with(['--conf', self.cwd+'/bad.conf', 'echo', 'foo'])
        self.assertTrue(output.find("warning: couldn't open config: File contains parsing errors: "))

    def test_missing_config(self):
        output = self._except_with(['--conf', self.cwd+'/missing.conf', 'echo', 'foo'])
        self.assertTrue(output.find("warning: failed to open config file '%s/missing.conf' : No such file or directory" % self.cwd))

    def _generate_with_conf(self, confname):
        self._run_with(['--conf', self.cwd+'/%s.conf' % confname, '--generate'])

    def _run_with(self, args):
        p = subprocess.Popen(['python', self.progname] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = p.communicate()[0]

        if p.returncode != 0:
            self.fail('Returned %s unexpectedly: %s' % (p.returncode, output))

        return output.strip()

    def _except_with(self, args):
        p = subprocess.Popen(['python', self.progname] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = p.communicate()[0]

        if p.returncode == 0:
            self.fail('Returned 0 unexpectedly (should be non-zero): %s' % output)

        return output.strip()

if __name__ == '__main__':
    unittest.main()
