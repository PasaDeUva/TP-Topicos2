import unittest

from validate_commit_message import is_valid_subject


class ConventionalCommitTests(unittest.TestCase):
    def test_accepts_valid_subjects(self) -> None:
        for subject in (
            "feat: add event search",
            "fix(auth): handle expired token",
            "refactor(api)!: change response shape",
            "chore(deps): update tooling",
        ):
            with self.subTest(subject=subject):
                self.assertTrue(is_valid_subject(subject))

    def test_rejects_invalid_subjects(self) -> None:
        for subject in (
            "Add event search",
            "Feat: add event search",
            "fix(auth):missing space",
            "feat: ",
            "feat(): add event search",
            "",
        ):
            with self.subTest(subject=subject):
                self.assertFalse(is_valid_subject(subject))


if __name__ == "__main__":
    unittest.main()
