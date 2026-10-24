"""Exercise the actual tmux expansion and terminal feature contracts in a disposable server."""
import fcntl
import json
import os
from pathlib import Path
import pty
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('tmux'), 'tmux required')
class TmuxIntegrationTests(unittest.TestCase):
    def test_literal_paths_and_idempotent_terminal_features(self):
        name = 'status-test-' + uuid.uuid4().hex[:8]
        def tmux(*args):
            return subprocess.run(['tmux', '-L', name, *args], capture_output=True, text=True, check=True).stdout.strip()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root / 'repo-$(printf INJECTED) with space'
            cwd.mkdir()
            result = root / 'result.json'
            widget = root / 'widget.py'
            widget.write_text('import json,sys\nfrom pathlib import Path\nPath(' + repr(str(result)) + ').write_text(json.dumps(sys.argv[1:]))\nprint("status")\n')
            lines = (ROOT / 'dot_tmux.conf.tmpl').read_text().splitlines()
            source = next(line for line in lines if "'status-format[1]'" in line)
            source = source.replace('~/.tmux/codex-statusline', shlex.quote(sys.executable) + ' ' + shlex.quote(str(widget)))
            features = [line for line in lines if line.startswith('set -s terminal-features[')]
            # A PTY without Ghostty is enough to check tmux's feature propagation.
            config = root / 'tmux.conf'
            config.write_text('\n'.join(features).replace('xterm-ghostty:', 'xterm-256color:') + '\nset -g status 2\n' + source + '\n')
            client = None
            master = slave = None
            try:
                tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'test', '-c', str(cwd), 'sleep', '30')
                tmux('set', '-p', '@codex_workdir', str(cwd))
                tmux('source-file', str(config))
                first = tmux('show-options', '-s', 'terminal-features')
                tmux('source-file', str(config))
                self.assertEqual(tmux('show-options', '-s', 'terminal-features'), first)
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 120, 0, 0))
                client = subprocess.Popen(['tmux', '-L', name, 'attach', '-t', 'test'], stdin=slave, stdout=slave,
                                          stderr=slave, env=dict(os.environ, TERM='xterm-256color'))
                for _ in range(40):
                    if result.exists():
                        break
                    time.sleep(.1)
                args = json.loads(result.read_text())
                self.assertEqual(Path(args[1]).resolve(), cwd.resolve())
                self.assertEqual(args[4], str(cwd))
                self.assertIn('sync', tmux('list-clients', '-F', '#{client_termfeatures}').split(','))
            finally:
                subprocess.run(['tmux', '-L', name, 'kill-server'], capture_output=True)
                if client:
                    client.wait(timeout=3)
                for fd in [master, slave]:
                    if fd is not None:
                        os.close(fd)


if __name__ == '__main__':
    unittest.main()
