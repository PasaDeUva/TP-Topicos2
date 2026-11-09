import re
import sys
from pathlib import Path


CONVENTIONAL_COMMIT = re.compile(
    r"^[a-z]+(?:\([a-z0-9][a-z0-9._/-]*\))?!?: \S.*$"
)


def is_valid_subject(subject: str) -> bool:
    return CONVENTIONAL_COMMIT.fullmatch(subject) is not None


def main() -> int:
    if len(sys.argv) == 2:
        lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
        subject = lines[0] if lines else ""
    elif len(sys.argv) == 3 and sys.argv[1] == "--subject":
        subject = sys.argv[2]
    else:
        print(
            "Usage: validate_commit_message.py <message-file> | --subject <subject>",
            file=sys.stderr,
        )
        return 2

    if not is_valid_subject(subject):
        print(
            f"Invalid commit subject: {subject!r}. "
            "Expected Conventional Commits format.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
