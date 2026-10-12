"""Independent deployment gate adversarial tests. Never uses live cloud credentials."""
import unittest
from cosmic_love_controller.controller import check,Hold,theorem,promote
SHA="0aa851628db8c4c09e7a9a7163731b9a09cc5dd8"
def fake(sha=SHA,status="success",paths=None,branch="cosmic-love-closure-review-20261013"):
 def get(u):
  if u.endswith("/pulls/29"):
   return {"number":29,"state":"open","draft":True,"merged":False,
    "head":{"sha":sha,"ref":branch,"repo":{"full_name":"letsgo0226/Notes"}},
    "base":{"ref":"main"}}
  if "/actions/runs?" in u:
   return {"workflow_runs":[{"id":777,"head_sha":sha,
    "name":"Cosmic Love — finite TM closure smoke","event":"pull_request",
    "status":"completed","conclusion":status}]}
  if "/pulls/29/files?" in u:
   files=paths if paths is not None else ["cosmic_love/closure_worker.py",
    ".github/workflows/cosmic_love_smoke.yml"]
   return [{"filename":x} for x in files]
  raise AssertionError("unknown GET")
 return get
class ControllerTests(unittest.TestCase):
 def test_reference_tm(self):self.assertEqual(theorem(),"FINITE_REFERENCE_CLOSED_LOOP_VERIFIED")
 def test_canary_is_not_primary_promotion(self):
  d=check(SHA,fake())
  self.assertEqual(d["status"],"CANARY_ELIGIBLE_NOT_DEPLOYED")
  self.assertFalse(d["primary_replacement"])
  self.assertFalse(d["live_trading"])
 def test_wrong_sha(self):
  with self.assertRaises(Hold):check("invalid",fake())
 def test_stale_pr_sha(self):
  with self.assertRaises(Hold):check(SHA,fake(sha="a"*40))
 def test_unexpected_branch(self):
  with self.assertRaises(Hold):check(SHA,fake(branch="main"))
 def test_failing_ci(self):
  with self.assertRaises(Hold):check(SHA,fake(status="failure"))
 def test_nonmatching_ci(self):
  with self.assertRaises(Hold):check(SHA,fake(status=None))
 def test_sensitive_cross_project_file(self):
  with self.assertRaises(Hold):check(SHA,fake(paths=["trader_42/bot.py"]))
 def test_empty_file_scope(self):
  with self.assertRaises(Hold):check(SHA,fake(paths=[]))
 def test_no_signed_backups(self):
  with self.assertRaisesRegex(Hold,"BACKUP"):
   promote(check(SHA,fake()),False,False)
 def test_no_boolean_backup_bypass(self):
  with self.assertRaisesRegex(Hold,"EXTERNAL_RECOVERY"):
   promote(check(SHA,fake()),True,True)
 def test_forged_canary_receipt(self):
  with self.assertRaises(Hold):promote({"status":"SUCCESS"},True,True)
if __name__=="__main__":unittest.main()
