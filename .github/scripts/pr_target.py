import sys


def target_for_branch(branch: str) -> str | None:
    if branch.startswith(("feature/", "bugfix/")):
        return "development"
    if branch.startswith(("release/", "hotfix/")):
        return "master"
    return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: pr_target.py <branch>")

    target = target_for_branch(sys.argv[1])
    if target is None:
        raise SystemExit(f"Unsupported branch: {sys.argv[1]}")

    print(target)
