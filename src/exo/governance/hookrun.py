"""Lo que hace cada git hook del motor (`exo hook <nombre>`, D-21 y D-29).

- `commit-msg`: asunto de Conventional Commits; un footer `Refs:` tiene que cumplir
  el patrón de tickets del proyecto. Sin `Refs:` se acepta, porque la persona
  puede haber confirmado que no hay ticket (ADR-0012).
- `pre-commit`: secretos y datos personales en las líneas agregadas del stage
  (con los waivers vigentes), archivos de credenciales y speclint de los
  artefactos SDD en el stage.
- `pre-push`: nada directo a las ramas protegidas, ni force-push, ni borrarlas;
  después, `exo check` sobre lo que se empuja.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from exo import _meta
from exo.core import config, scan, tickets, waivers
from exo.governance import git
from exo.sdd import speclint, specs

TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)
MAX_SUBJECT = 72
_SUBJECT = re.compile(rf"^(?:{'|'.join(TYPES)})(?:\([^()\s][^()]*\))?!?: \S")
_AUTO = re.compile(r"^(?:Merge |Revert \"|fixup! |squash! |amend! )")
_REFS = re.compile(r"^Refs:\s*(.*?)\s*$", re.IGNORECASE)
_TICKET_FIRST = re.compile(r"^\S+\s+(?:" + "|".join(TYPES) + r")\b")
_SCISSORS = "# ------------------------ >8 ------------------------"
# Archivos que no se commitean nunca (el ejemplo, sí).
BLOCKED_FILES = (
    ".env",
    ".env.*",
    "*.pem",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
)
ALLOWED_FILES = (".env.example", ".env.sample", ".env.template")


@dataclass
class HookResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


# -- commit-msg -------------------------------------------------------------------------------


def _message_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith(_SCISSORS):
            break
        if not line.startswith("#"):
            lines.append(line.rstrip())
    return lines


def check_message(text: str, *, pattern: str | None, example: str | None) -> HookResult:
    result = HookResult()
    lines = _message_lines(text)
    subject = next((line for line in lines if line.strip()), "")
    if not subject:
        result.errors.append("the commit message is empty")
        return result
    if _AUTO.match(subject):
        return result
    if not _SUBJECT.match(subject):
        hint = ""
        if _TICKET_FIRST.match(subject):
            hint = " Put the ticket in a `Refs: <ticket>` footer, not in the subject."
        result.errors.append(
            f"the subject {subject!r} is not Conventional Commits: write "
            f"`<type>(<scope>): <summary>`, with a type from {', '.join(TYPES)}.{hint}"
        )
    elif len(subject) > MAX_SUBJECT:
        result.warnings.append(
            f"the subject has {len(subject)} characters; keep it to {MAX_SUBJECT}"
        )
    for line in lines:
        match = _REFS.match(line)
        if not match or pattern is None:
            continue
        for value in (v.strip() for v in match.group(1).split(",")):
            try:
                tickets.validate_ticket(value, pattern, example)
            except tickets.TicketError as exc:
                result.errors.append(f"Refs: {exc}")
    return result


def commit_msg(project: Path, message_file: Path) -> HookResult:
    cfg = config.load(project).config
    text = Path(message_file).read_text(encoding="utf-8", errors="replace")
    return check_message(text, pattern=cfg["tickets"]["pattern"], example=cfg["tickets"]["example"])


# -- pre-commit -------------------------------------------------------------------------------


def _blocked(rel: str) -> bool:
    name = PurePosixPath(rel).name
    if name in ALLOWED_FILES:
        return False
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in BLOCKED_FILES)


def _is_sdd(project: Path, rel: str, specs_dir: str) -> bool:
    path = PurePosixPath(rel)
    if not path.is_relative_to(PurePosixPath(specs_dir)):
        return False
    if path.name == specs.SPEC_FILE and path.parent.parent.name == specs.CAPABILITIES:
        return True
    return path.name in speclint.ARTIFACTS


def scan_added(project: Path, added: dict[str, list[tuple[int, str]]], cfg: dict) -> HookResult:
    """Secretos y datos personales en líneas agregadas, con los waivers vigentes."""
    result = HookResult()
    loaded = waivers.load(project)
    result.warnings += loaded.problems
    pii = cfg["data_protection"]["pii"]
    for rel, lines in sorted(added.items()):
        for finding in scan.scan_lines(lines, pii=pii):
            waiver = waivers.covers(loaded, finding, rel)
            if waiver is not None:
                continue
            what = "a secret" if finding.level == scan.CRITICAL else "personal data"
            fix = (
                "remove it and rotate it if it was real"
                if finding.level == scan.CRITICAL
                else f"remove it, or add a waiver in {_meta.PROJECT_DIR}/{waivers.FILENAME}"
            )
            result.errors.append(
                f"{rel}:{finding.line}: {what} ({finding.kind}, {finding.excerpt}): {fix}"
            )
    return result


def pre_commit(project: Path) -> HookResult:
    project = Path(project)
    cfg = config.load(project).config
    result = HookResult()
    staged = git.staged_files(project)
    for rel in staged:
        if _blocked(rel):
            result.errors.append(
                f"{rel}: credential files are never committed; unstage it (`git restore --staged "
                f"{rel}`) and keep it out with .gitignore"
            )
    found = scan_added(project, git.added_lines(project, "--cached", "--diff-filter=ACMR"), cfg)
    result.errors += found.errors
    result.warnings += found.warnings
    for rel in staged:
        if not _is_sdd(project, rel, cfg["specs_dir"]) or not (project / rel).is_file():
            continue
        try:
            report = speclint.lint_path(project / rel)
        except (speclint.SpeclintError, OSError, UnicodeDecodeError) as exc:
            result.errors.append(f"{rel}: {exc}")
            continue
        for item in report.files:
            result.errors += [f"{rel}:{issue.line}: {issue.message}" for issue in item.errors]
    return result


# -- pre-push --------------------------------------------------------------------------------


@dataclass(frozen=True)
class PushRef:
    local_ref: str
    local_sha: str
    remote_ref: str
    remote_sha: str

    @property
    def remote_branch(self) -> str:
        prefix = "refs/heads/"
        return self.remote_ref[len(prefix) :] if self.remote_ref.startswith(prefix) else ""

    @property
    def deleting(self) -> bool:
        return git.is_zero(self.local_sha)

    @property
    def creating(self) -> bool:
        return git.is_zero(self.remote_sha)


def parse_push_lines(lines: list[str]) -> list[PushRef]:
    refs: list[PushRef] = []
    for line in lines:
        parts = line.split()
        if len(parts) == 4:
            refs.append(PushRef(*parts))
    return refs


def pre_push(project: Path, remote: str, lines: list[str]) -> HookResult:
    from exo.sdd import check

    project = Path(project)
    cfg = config.load(project).config
    protected = set(cfg["governance"]["protected_branches"])
    result = HookResult()
    refs = parse_push_lines(lines)
    for ref in refs:
        branch = ref.remote_branch
        if branch in protected:
            action = "deleting" if ref.deleting else "pushing straight to"
            result.errors.append(
                f"{action} the protected branch {branch} is not allowed: open a pull request "
                "from a feature branch instead"
            )
            continue
        if ref.deleting or ref.creating:
            continue
        ancestor = git.is_ancestor(project, ref.remote_sha, ref.local_sha)
        if ancestor is False:
            result.errors.append(
                f"force-push to {branch}: the remote has commits that yours does not (rewritten "
                "history). Merge or rebase onto it instead of overwriting it"
            )
        elif ancestor is None:
            result.errors.append(
                f"cannot tell whether the push to {branch} rewrites history (the remote commit "
                "is not here); run `git fetch` and push again"
            )
    if result.errors:
        return result
    for ref in refs:
        if ref.deleting or ref.creating:
            continue
        try:
            outcome = check.check(project, base=ref.remote_sha, fast=True)
        except check.CheckError as exc:
            result.warnings.append(f"{_meta.NAME} check did not run: {exc}")
            continue
        for item in outcome.changes:
            result.errors += [
                f"{f.path}: {f.message}" for f in item.findings if f.severity == "error"
            ]
        result.errors += [f.message for f in outcome.diff if f.severity == "error"]
    return result
