"""Static policy checks for CLSDP GitHub Actions safety gates."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'clsdp_research.yml'
README = ROOT / 'research' / 'clsdp' / 'README.md'


class CLSDPWorkflowPolicyTests(unittest.TestCase):
    def test_public_network_and_draft_jobs_require_explicit_repo_variable(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn("vars.CLSDP_ALLOW_SCHEDULED_RESEARCH == 'true'", text)
        self.assertEqual(text.count("vars.CLSDP_ALLOW_SCHEDULED_RESEARCH == 'true'"), 2)
        for job in ('public-research', 'draft-review'):
            match = re.search(rf"\n  {job}:\n(?P<body>.*?)(?=\n  [a-zA-Z0-9_-]+:|\Z)", text, re.S)
            self.assertIsNotNone(match, job)
            body = match.group('body')
            self.assertIn("github.event_name != 'pull_request'", body)
            self.assertIn("github.ref == 'refs/heads/main'", body)
            self.assertIn("vars.CLSDP_ALLOW_SCHEDULED_RESEARCH == 'true'", body)
        offline = re.search(r"\n  offline-tests:\n(?P<body>.*?)(?=\n  [a-zA-Z0-9_-]+:|\Z)", text, re.S).group('body')
        self.assertNotIn('vars.CLSDP_ALLOW_SCHEDULED_RESEARCH', offline)

    def test_no_deploy_or_secret_touching_keywords_in_workflow(self):
        text = WORKFLOW.read_text(encoding='utf-8').lower()
        forbidden = [
            'railway', 'binance_api_key', 'binance_secret', 'live_armed',
            'live_dry_run', 'hsi_order_kill', 'deployments', 'environment_variables',
        ]
        for word in forbidden:
            with self.subTest(word=word):
                self.assertNotIn(word, text)

    def test_readme_documents_variable_as_research_only_not_trade_authority(self):
        text = README.read_text(encoding='utf-8')
        self.assertIn('CLSDP_ALLOW_SCHEDULED_RESEARCH', text)
        self.assertIn('research-automation opt-in', text)
        self.assertIn('not a broker or\ntrading authorization', text)
        self.assertIn('only the offline tests run', text)


if __name__ == '__main__':
    unittest.main()
