#!/usr/bin/env python3

from importlib.machinery import SourceFileLoader
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).parents[1] / "dot_local/bin/executable_codex-tab-title-hook"
hook = SourceFileLoader("codex_tab_title_hook", str(SOURCE)).load_module()


def response_item(text: str) -> str:
    return json.dumps(
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            },
        },
        ensure_ascii=False,
    )


class MarkerTests(unittest.TestCase):
    def test_current_html_marker(self):
        self.assertEqual(
            hook.extract_text_marker("<!-- codex-tab-title: 탭 제목 훅 개편 -->\n진행합니다."),
            "탭 제목 훅 개편",
        )

    def test_historical_literal_destination(self):
        self.assertEqual(
            hook.extract_text_marker('[codex-tab-title]: <codex-title> "탭 제목 훅 개편"'),
            "탭 제목 훅 개편",
        )

    def test_historical_substituted_destination(self):
        self.assertEqual(
            hook.extract_text_marker(
                '[codex-tab-title]: 스카우터 성능 모니터링 "스카우터 성능 모니터링"'
            ),
            "스카우터 성능 모니터링",
        )

    def test_last_marker_wins(self):
        raw = "\n".join(
            [
                response_item("<!-- codex-tab-title: 초기 조사 -->"),
                response_item("<!-- codex-tab-title: 배포 훅 보강 -->"),
            ]
        )
        self.assertEqual(hook.extract_marker(raw), "배포 훅 보강")

    def test_agent_message_rollout_shape(self):
        raw = json.dumps(
            {
                "type": "event_msg",
                "payload": {
                    "type": "item_completed",
                    "item": {
                        "type": "AgentMessage",
                        "content": [
                            {
                                "type": "Text",
                                "text": "<!-- codex-tab-title: 이벤트 훅 검증 -->",
                            }
                        ],
                    },
                },
            },
            ensure_ascii=False,
        )
        self.assertEqual(hook.extract_marker(raw), "이벤트 훅 검증")

    def test_wide_title_respects_tmux_budget(self):
        self.assertEqual(hook.truncate_columns("가" * 13), "가" * 12)

    def test_control_characters_are_removed(self):
        self.assertEqual(hook.clean_title("안전\x1b]2;오염"), "안전 ]2;오염")

    def test_incomplete_jsonl_is_not_consumed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            complete = response_item("<!-- codex-tab-title: 첫 제목 -->") + "\n"
            path.write_bytes((complete + '{"type":"partial').encode())
            raw, offset = hook.read_complete_jsonl(path, 0)
            self.assertEqual(hook.extract_marker(raw), "첫 제목")
            self.assertEqual(offset, len(complete.encode()))


@unittest.skipUnless(shutil.which("tmux"), "tmux is required")
class TmuxIntegrationTests(unittest.TestCase):
    def test_prompt_reconcile_and_clear(self):
        tmux = shutil.which("tmux")
        assert tmux is not None
        socket_name = f"codex-title-test-{os.getpid()}"
        subprocess.run(
            [tmux, "-L", socket_name, "-f", "/dev/null", "new-session", "-d", "-s", "test"],
            check=True,
        )
        try:
            pane = subprocess.check_output(
                [tmux, "-L", socket_name, "display-message", "-p", "#{pane_id}"],
                text=True,
            ).strip()
            socket_path = subprocess.check_output(
                [tmux, "-L", socket_name, "display-message", "-p", "#{socket_path}"],
                text=True,
            ).strip()
            server_pid = subprocess.check_output(
                [tmux, "-L", socket_name, "display-message", "-p", "#{pid}"],
                text=True,
            ).strip()
            with tempfile.TemporaryDirectory() as directory:
                env = {
                    **os.environ,
                    "HOME": directory,
                    "TMUX": f"{socket_path},{server_pid},0",
                    "TMUX_PANE": pane,
                }
                transcript = Path(directory) / "rollout.jsonl"
                transcript.write_text("", encoding="utf-8")
                prompt_input = {
                    "session_id": "session-test",
                    "turn_id": "turn-test",
                    "transcript_path": str(transcript),
                    "prompt": "탭 제목 훅을 검증해줘",
                }
                started = subprocess.run(
                    [sys.executable, str(SOURCE)],
                    input=json.dumps(prompt_input),
                    env=env,
                    text=True,
                    check=True,
                    capture_output=True,
                )
                self.assertIn("additionalContext", started.stdout)
                with transcript.open("a", encoding="utf-8") as handle:
                    handle.write(response_item("<!-- codex-tab-title: 통합 훅 검증 -->") + "\n")
                subprocess.run(
                    [sys.executable, str(SOURCE), "--reconcile"],
                    input=json.dumps({"hook_event_name": "PostToolUse"}),
                    env=env,
                    text=True,
                    check=True,
                )
                title = subprocess.check_output(
                    [tmux, "-L", socket_name, "show-options", "-p", "-v", "-t", pane, "@agent_title"],
                    text=True,
                ).strip()
                self.assertEqual(title, "통합 훅 검증")
                subprocess.run(
                    [sys.executable, str(SOURCE), "--clear"],
                    input="{}",
                    env=env,
                    text=True,
                    check=True,
                )
                cleared = subprocess.run(
                    [tmux, "-L", socket_name, "show-options", "-p", "-v", "-t", pane, "@agent_title"],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(cleared.returncode, 0)
        finally:
            subprocess.run([tmux, "-L", socket_name, "kill-server"], check=False)


if __name__ == "__main__":
    unittest.main()
