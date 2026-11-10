import unittest

from pr_target import target_for_branch


class PullRequestTargetTests(unittest.TestCase):
    def test_feature_and_bugfix_target_development(self) -> None:
        for branch in ("feature/example", "bugfix/example"):
            with self.subTest(branch=branch):
                self.assertEqual(target_for_branch(branch), "development")

    def test_release_and_hotfix_target_master(self) -> None:
        for branch in ("release/1.0", "hotfix/example"):
            with self.subTest(branch=branch):
                self.assertEqual(target_for_branch(branch), "master")

    def test_unmanaged_branches_have_no_target(self) -> None:
        for branch in ("development", "master", "feature", "docs/example"):
            with self.subTest(branch=branch):
                self.assertIsNone(target_for_branch(branch))


if __name__ == "__main__":
    unittest.main()
