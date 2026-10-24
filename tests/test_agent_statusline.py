import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    scope = runpy.run_path(str(ROOT / name))
    return scope['print_status'].__globals__


class StatuslineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, TMPDIR=self.tmp.name)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.g = load('dot_tmux/executable_codex-statusline')
        self.a = load('dot_tmux/executable_agy-statusline')
        self.now = int(time.time())

    def test_weekly_selection_and_invalid_values(self):
        for value in [None, True, '20', float('nan'), float('inf'), -1, 101]:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.g['extract_state']({'rateLimits': {'secondary': {
                    'windowDurationMins': 10080, 'usedPercent': value, 'resetsAt': self.now + 1000}}})
        state = self.g['extract_state']({'rateLimits': {
            'primary': {'windowDurationMins': 10080, 'usedPercent': 80, 'resetsAt': self.now + 1000},
            'secondary': {'windowDurationMins': 300, 'usedPercent': 10, 'resetsAt': self.now + 1000}}})
        self.assertEqual(state['remaining_percent'], 20)
        with self.assertRaises(RuntimeError):
            self.g['extract_state']({'rateLimits': {'secondary': {'windowDurationMins': 300}}})

    def test_expired_and_missing_context_are_not_available_credit(self):
        for timestamp, fetched in [(self.now - 1, self.now), (self.now + 1000, self.now - 10000)]:
            state = dict(remaining_percent=88, resets_at=timestamp, fetched_at=fetched)
            for render, args in [(self.g['render_line'], ('CODEX', state, None)),
                                 (self.a['render'], (None, state, 140, ''))]:
                text = render(*args)
                self.assertNotIn('88%', text)
                self.assertNotIn('0%', text)

    def test_rpc_batched_and_split_frames(self):
        fake = Path(self.tmp.name) / 'fake-agent'
        for split in [False, True]:
            fake.write_text('#!' + sys.executable + '\nimport os,time\n' +
                            'os.write(1,b\'{"id":0,"result":{}}\\n{"id":1,"res\')\n' +
                            ('time.sleep(.03)\n' if split else '') +
                            'os.write(1,b\'ult":{"valid":true}}\\n\')\ntime.sleep(2)\n')
            fake.chmod(0o700)
            with patch.dict(self.g, codex_binary=lambda: str(fake), FETCH_TIMEOUT_SECONDS=1):
                self.assertEqual(self.g['app_server_request'](), {'valid': True})

    def test_failed_refresh_is_throttled(self):
        owner = dict(pid=1, started='birth', home=self.tmp.name, tool='codex')
        with patch.dict(self.g, owner_for_pane=lambda *a: owner,
                        read_cache=lambda: dict(fetched_at=self.now-500, error_at=self.now, line='error'),
                        rollout_for_pid=lambda *a: None, latest_context_state=lambda *a: None), \
             patch.dict(self.g, start_background_refresh=unittest.mock.Mock()) as scope, \
             patch.object(sys, 'argv', ['status', 'codex', '/tmp', '140', '1']), \
             contextlib.redirect_stdout(io.StringIO()):
            self.g['print_status']()
            self.g['print_status']()
            scope['start_background_refresh'].assert_not_called()

    def test_primary_agent_wins_over_tool_children_and_one_snapshot(self):
        rows = {1: dict(pid=1, ppid=0, started='a', command='zsh'),
                2: dict(pid=2, ppid=1, started='b', command='codex'),
                3: dict(pid=3, ppid=2, started='c', command='claude')}
        snapshot = unittest.mock.Mock(return_value=rows)
        with patch.dict(self.g, process_snapshot=snapshot, process_home=lambda *a: self.tmp.name):
            self.assertEqual(self.g['owner_for_pane'](1)['tool'], 'codex')
            self.assertIsNone(self.g['claude_pid_for_pane'](1))
            self.assertEqual(self.g['codex_pid_for_pane'](1), 2)
            snapshot.assert_called_once()
        self.assertIsNone(self.g['agent_kind']('/bin/echo claude'))
        self.assertEqual(self.g['agent_kind']('node /bin/codex.js'), 'codex')

    def test_process_environment_failure_does_not_choose_default_account(self):
        with patch.object(subprocess, 'run', side_effect=OSError), \
             patch.object(Path, 'read_bytes', side_effect=OSError):
            self.assertIsNone(self.g['process_home'](123, 'claude'))

    def test_context_cache_skips_unchanged_rollout(self):
        path = Path(self.tmp.name) / 'rollout.jsonl'
        def event(tokens):
            return json.dumps(dict(type='event_msg', payload=dict(type='token_count', info=dict(
                model_context_window=1000, last_token_usage=dict(total_tokens=tokens))))) + '\n'
        path.write_text(event(100) + event(550))
        expected = self.g['latest_context_state']('/irrelevant', str(path))
        with patch.dict(self.g, tail_lines=unittest.mock.Mock(side_effect=AssertionError('rescanned'))):
            self.assertEqual(self.g['latest_context_state']('/irrelevant', str(path)), expected)
        path.write_text(event(20))
        self.assertEqual(self.g['latest_context_state'](None, str(path))['tokens'], 20)
        self.assertIsNone(self.g['latest_context_state']('/same-directory'))

    def test_claude_sessions_are_bound_to_process_birth_and_home(self):
        writer = ROOT / 'dot_claude/executable_tmux-status-cache.py'
        home = Path(self.tmp.name) / 'claude'
        def write(pid, sid, used):
            payload = dict(session_id=sid, cwd='/same-directory', context_window=dict(used_percentage=used),
                           rate_limits=dict(seven_day=dict(used_percentage=30, resets_at=self.now+1000)))
            result = subprocess.CompletedProcess([], 0, f'{pid} 1 Wed Oct 21 12:00:00 2026 claude\n')
            with patch.dict(os.environ, CLAUDE_CONFIG_DIR=str(home), STATUSLINE_OWNER_PID=str(pid)), \
                 patch.object(subprocess, 'run', return_value=result), \
                 patch.object(sys, 'stdin', io.StringIO(json.dumps(payload))), \
                 contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(writer))
        write(101, 'session-a', 10)
        write(102, 'session-b', 80)
        with patch.dict(self.g, ACTIVE_CLAUDE_CONFIG_DIR=home):
            for pid, expected in [(101, 10), (102, 80)]:
                owner = dict(pid=pid, started='Wed Oct 21 12:00:00 2026')
                self.assertEqual(self.g['latest_claude_state'](owner)['context_used_percent'], expected)
            self.assertIsNone(self.g['latest_claude_state'](dict(pid=101, started='new birth')))
            self.assertIsNone(self.g['latest_claude_state'](dict(pid=103, started='Wed Oct 21 12:00:00 2026')))
        with patch.dict(self.g, ACTIVE_CLAUDE_CONFIG_DIR=home / 'other'):
            self.assertIsNone(self.g['latest_claude_state'](dict(pid=101, started='Wed Oct 21 12:00:00 2026')))
        write(101, 'session-a', None)
        with patch.dict(self.g, ACTIVE_CLAUDE_CONFIG_DIR=home):
            self.assertIsNone(self.g['latest_claude_state'](dict(pid=101, started='Wed Oct 21 12:00:00 2026'))['context_used_percent'])

    def test_agy_uses_supplied_owner_and_never_directory_fallback(self):
        with patch.dict(os.environ, STATUSLINE_AGENT_PID='42'), \
             patch.dict(self.a, agy_pid_for_pane=unittest.mock.Mock(side_effect=AssertionError('extra scan')),
                        conversation_for_pid=lambda pid: None,
                        conversation_for_cwd=unittest.mock.Mock(side_effect=AssertionError('wrong session')),
                        read_cache=lambda: dict(fetched_at=self.now), account_label=lambda: ''), \
             patch.object(sys, 'argv', ['status', 'agy', '/same', '140', '1']), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.a['print_status']()
            self.assertIn('—', output.getvalue())

    def test_agy_invalid_quota_is_not_clamped_to_free_credit(self):
        for value in [None, True, '0', float('nan'), -1, 2]:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.a['extract_state']({'command': {'data': {'groups': [{'name': 'Gemini', 'buckets': [
                    {'window': 'weekly', 'remaining_fraction': value, 'reset_time': '2030-01-01T00:00:00Z'}]}]}}})

    def test_idle_pane_cache_invalidates_on_command_change(self):
        with patch.dict(self.g, process_snapshot=unittest.mock.Mock(return_value={})) as scope:
            self.assertIsNone(self.g['owner_for_pane'](123, 'zsh'))
            self.g['_owner_bindings'] = {}
            self.assertIsNone(self.g['owner_for_pane'](123, 'zsh'))
            scope['process_snapshot'].assert_called_once()
            self.g['_owner_bindings'] = {}
            self.assertIsNone(self.g['owner_for_pane'](123, 'codex'))
            self.assertEqual(scope['process_snapshot'].call_count, 2)

    def test_absent_rollout_and_unchanged_empty_transcripts_are_cached(self):
        empty = subprocess.CompletedProcess([], 0, '')
        with patch.object(subprocess, 'run', return_value=empty) as run:
            self.assertIsNone(self.g['rollout_for_pid'](123, 'birth'))
            self.assertIsNone(self.g['rollout_for_pid'](123, 'birth'))
            run.assert_called_once()
        path = Path(self.tmp.name)/'empty.jsonl'
        path.write_text('{}\n')
        for scope, function, args in [(self.g, 'latest_context_state', (None, str(path))),
                                       (self.a, 'context_used_percent', (path,))]:
            self.assertIsNone(scope[function](*args))
            with patch.dict(scope, tail_lines=unittest.mock.Mock(side_effect=AssertionError('rescanned'))):
                self.assertIsNone(scope[function](*args))
        with patch.dict(os.environ, STATUSLINE_AGENT_STARTED='birth'), \
             patch.object(subprocess, 'run', return_value=empty) as run:
            self.assertIsNone(self.a['conversation_for_pid'](123))
            self.assertIsNone(self.a['conversation_for_pid'](123))
            run.assert_called_once()

    def test_timer_does_not_force_seconds_redraw(self):
        for scope in [self.g, self.a]:
            self.assertEqual(scope['countdown_text'](3601), scope['countdown_text'](3605))


if __name__ == '__main__':
    unittest.main()
