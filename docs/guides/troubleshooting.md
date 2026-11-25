# Troubleshooting

Start with the diagnosis. It checks Python, the console, the `PATH`, the engine's content, the project installation, the git hooks, each agent, the memory and your data folder, and says what to do for each warning:

```sh
exo doctor
exo status
```

Most commands take `--json` (all but `exo codeowners`, `exo persona set`, `exo persona clear`, `exo backups pin`, `exo backups unpin`, `exo hook` and `exo mcp`), and `exo <command> --help` lists its options. Below are the messages you are most likely to see, as exo prints them, with the fix.

## Installing exo

**`Python 3.10 or later not found`**
The installer found no usable Python and no uv. Install Python 3.10 or later (from python.org, `winget` or your package manager), or install uv, which brings its own Python, and run the installer again.

**`Could not create the venv: install the python3-venv package or install uv.`**
Some Linux distributions ship Python without `venv`. Install that package, or install uv.

**`/home/you/.local/bin/exo already exists and does not belong to this engine (another tool called exo?).`**
There is another program called `exo` (an unrelated project uses the name). The installer never overwrites it: move or delete it and retry.

**`git is required to install <ref> with uv.`**
With uv, the installer installs from the git repository. Install git, or set `EXO_INSTALL_NO_UV=1` to install the release wheel with pip instead (that path checks `SHA256SUMS`).

**`Checksum mismatch for <wheel>: SHA256SUMS says ..., the download is .... Nothing was installed`**
The downloaded wheel is not the one the release lists. Nothing changed on your machine. Retry; if it happens again, report it.

**`Cannot verify release v1.0.0: could not download .../SHA256SUMS. Nothing was installed.`**
Without uv, a release installs only after its wheel is checked against its `SHA256SUMS`, and the installer could not get them. Check the connection and that the tag exists in the repository's releases, then retry.

**`curl is required to download ...: wget follows redirects to http, where the download could be swapped. Install curl and retry.`**
On macOS and Linux without uv, the installer downloads with `curl`, which it can keep on `https` through every redirect. Install curl.

**`... redirected to ..., which is not https; refusing it.`** (`install.ps1`)
A download was redirected to another protocol, where it could be swapped, and the installer stopped (`install.sh` stops the same way, with curl's error). Retry on another network, or report it.

**`EXO_REPO_URL must be an https:// URL`** and **`Not a valid tag, branch or commit`**
`EXO_REPO_URL` and `EXO_REF` are checked before anything is downloaded. Unset them to install the latest release from GitHub, or set `EXO_REF` to a release tag such as `v1.0.0`, or to a branch.

**`Could not reach https://github.com/julimonte03/exo-harness to find the latest release.`**
No connection, or GitHub did not answer. Check the connection or the proxy, or set `EXO_REF` to skip the lookup.

**`exo: command not found` right after installing**
The installer added exo to the `PATH` of new terminals ("Open a new terminal to use 'exo'"). Open one. If you passed `--no-path`, add the folder it printed yourself.

**The downloaded `install.ps1` does not run**
Windows blocks scripts by default. Run it with `powershell -ExecutionPolicy Bypass -File install.ps1`.

**`uvx exo` runs something else**
`uvx exo` runs a different package from PyPI that is also called `exo`. Keep `--from`: `uvx --from git+https://github.com/julimonte03/exo-harness exo init`.

## The `exo` on your PATH

**`` `exo` is not on the PATH; activate the environment or reinstall the engine ``** (`exo doctor`, line `path`)
Your shell does not find exo. Open a new terminal, activate the virtual environment you installed it in, or run the installer again.

**``the first `exo` on the PATH (...) is not this engine (...); it may be another project with the same name``**
Another `exo` comes first in your `PATH`. Remove it or move exo's folder ahead of it; `exo doctor` shows both paths.

## Installing in a project: init, sync and update

**`conflict: <path> (<kind>): modified by hand since the last install`**, then **`nothing was written. Review the conflicts or retry with --force (takes a snapshot first).`**
You (or someone) edited a file that exo generates. exo writes nothing and exits with 1. Choose:

- keep your change somewhere exo does not own: outside the marked block in `AGENTS.md`, `CLAUDE.md` or `.gitignore`, or in a file of your own;
- or overwrite it with `--force`. A snapshot comes first: `exo backups list` lists them and `exo restore <name>` brings one back.

`exo update` behaves differently: it keeps your edit (`kept: <path> (<kind>): modified by hand since the last install`) and exits with 1 so you notice; with `--apply` it writes the rest. The other files of that skill or subagent stay as they were too (`kept: <folder>/ (N files, left as it was: ...)`), so a skill is never half updated. `exo update --apply --force` overwrites your edit too.

**`unresolved: <path> (<kind>): already exists with different content and the engine did not generate it; move or delete it and retry (--force does not overwrite human files)`**
A file exo would generate already exists and is yours. `--force` never overwrites your files: move or rename yours and run the command again.

**``orphaned: N files that this content no longer ships were kept (your agents may still use them); delete them with `exo sync --prune` ``**
A newer exo no longer ships some skills or subagents, or renamed them (`exo update` shows a rename as such, for example `review` to `pre-commit-review`). They stay until you delete them with `exo sync --prune` or `exo update --apply --prune`. If they are in a folder that none of the project's agents reads, for example `.agents/skills/` after `exo remove-agent`, the message says so instead (`no agent of this project reads .agents/skills/`): nothing uses them.

**``the lock was written by exo 0.2.0; run `exo update` ``** (`exo doctor`, line `install`)
You upgraded exo; the project still has the files of the previous version. Run `exo update` to see what changes, then `exo update --apply`.

**`the lock was written by exo X, newer than this engine (Y): updating would take the project back to Y. Upgrade exo, or pass --force to do it anyway`** (`exo init`, `sync`, `update`, `add-agent` and `remove-agent`)
A teammate installed the project with a newer exo. Upgrade yours (run the installer again); nothing was written. `--force` writes anyway and takes the project back to your version, removing what the newer one added. For the same lock, `exo doctor` and `exo status` say `upgrade exo`. If the lock also uses a newer schema, every command that reads it says `the lock uses schema N and this engine understands up to M (a newer exo wrote it); upgrade exo and retry`, and `--force` does not change that.

**`.exo/config.json was written by a newer exo (schema N; this engine understands up to M); upgrade exo and retry`** (`exo init`, `sync`, `update`, `add-agent` and `remove-agent`)
A newer exo saved the project's config. Upgrade yours; nothing was written, and `--force` does not change that. Commands that only read the config, such as `exo doctor`, use the defaults until you upgrade, and say so.

**`.exo/config.json cannot be used (...). Fix it and retry: with the defaults, your agents' files would be removed.`**
The config has invalid JSON or invalid values. exo stops instead of guessing. Fix what the message lists in parentheses, or restore the file from git.

**``.exo/lock.json: agents must be a list of names; restore the project from a snapshot (`exo backups list`, then `exo restore <name>`)``** (or `packs`)
The lock was edited by hand or damaged. Restore it from git, or bring back a snapshot as the message says.

**`unknown agent: 'x' (known: claude-code, copilot, cursor, codex, gemini, devin, generic)`**
Use one of the listed names with `--agents`, `exo add-agent` or `exo remove-agent`.

**``the engine is not installed in <path>; run `exo init` ``**
The command needs an installed project, and there is no `.exo/lock.json` here. Run it from the project root, pass `--project <path>`, or run `exo init`.

**`failed partway through (...); snapshot <name> was restored`**
Something failed while writing (a locked file, a full disk). exo put back the snapshot it took before starting, so the project is as it was. Fix the cause in the parentheses and retry.

**`engine content not found (packs/); reinstall the package or set EXO_CONTENT_ROOT`**
The installation is incomplete. Run the installer again.

## Claude Code

**`open Claude Code once in the project and accept the workspace trust dialog`** (`exo doctor`, line `claude-trust`)
Claude Code applies the project's permissions, including the ones for `exo`, only in a trusted workspace. Open Claude Code in the project and accept the dialog.

**Claude Code asks before `exo init`, `exo sync`, `exo update` or `exo gate publish`**
That is on purpose: the project's permission covers only the commands that read, check and record. The ones that change the installation, delete or export memory, or run a command from the config ask you first. See the [Claude Code guide](claude-code.md#what-runs-without-asking).

**``Claude Code X may not read AGENTS.md without CLAUDE.md: update it to 2.1.281 or run `exo init --claude-md --yes` ``**
Older Claude Code versions read only `CLAUDE.md`. Update Claude Code, or let exo create a `CLAUDE.md` that imports `AGENTS.md`.

**The MCP server does not load**
Claude Code asks you to approve a project MCP server, and an organization policy can block it. The MCP server is optional: the agent uses the `exo` CLI either way.

## GitHub Copilot

**Copilot asks before every `exo` command**
That is Copilot's tool approval: exo does not write a Copilot permission rule yet. Approve the commands as they come. See the [Copilot guide](copilot.md).

**An exo skill does not load in Copilot**
Copilot uses the first skill it finds with a name, starting with `.github/skills/`. A skill of yours there with the same name hides exo's: rename yours.

**A subagent of your own has no shell in Copilot CLI on Windows**
Copilot CLI on Windows gives a custom agent no shell when its `tools` list `Bash` alone. List `PowerShell` too; `exo validate` reports a subagent of a pack that lists `Bash` without `PowerShell`.

## Git hooks

**`exo commit-msg: blocked`** with **`the subject '...' is not Conventional Commits`**
Write the subject as `<type>(<scope>): <summary>`, with a type from `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` or `revert`. If the project uses tickets, the ticket goes in a `Refs: <ticket>` footer, not in the subject.

**`<file>:<line>: a secret (<kind>, ...): remove it and rotate it if it was real`** (pre-commit)
A credential is staged. Remove it from the file; if it was real, rotate it, because it may already be elsewhere. Secrets have no exceptions.

**`<file>:<line>: personal data (<kind>, ...): remove it, or add a waiver in .exo/waivers.json`** (pre-commit)
Data such as a card number or an IBAN is staged. Remove it, or, for synthetic test data, ask the person with the `tech_lead` role to approve a waiver, with an expiry date and the narrowest path:

```json
{
  "waivers": [
    {
      "detector": "card",
      "path": "tests/fixtures/**",
      "reason": "Published test card numbers for the payment tests",
      "approved_by": "<tech lead>",
      "expires": "2027-06-30"
    }
  ]
}
```

**``<file>: credential files are never committed; unstage it (`git restore --staged <file>`) and keep it out with .gitignore``** (pre-commit)
Files such as `.env` or private keys (`id_rsa`) are blocked by name; examples such as `.env.example` are not. Unstage the file and add it to `.gitignore`.

**`pushing straight to the protected branch main is not allowed: open a pull request from a feature branch instead`** (pre-push)
`main` is in `governance.protected_branches`. Push a branch and open a pull request. A force-push that rewrites a branch's history is blocked the same way (`force-push to <branch>: the remote has commits that yours does not`): merge or rebase instead.

**``cannot tell whether the push to <branch> rewrites history (the remote commit is not here); run `git fetch` and push again``**
Fetch and push again.

**`exo: not found in PATH, so the <hook> hook did not run; CI still runs exo check`**
The hook ran in a process that does not see exo, typical of graphical git clients and editors on macOS. Set `EXO_HOOK_CMD` to the full path of `exo` in that environment, or start the client from a terminal. The hook does not block in this case: CI is still the real gate.

**``not active in this clone (core.hooksPath: it is not set); run `exo sync` ``** (`exo doctor`, line `githooks`)
Hooks are activated per clone. After cloning a project that uses exo, run `exo sync` once. If the clone already has hooks of its own in `.git/hooks`, exo does not activate its own and says so; add `exo hook <name>` to yours. With husky or the pre-commit framework, exo adds its steps there: `npm install` activates husky, and `exo doctor` prints the `pre-commit install` command when it is missing.

To turn the hooks off for a project, set `"githooks": false` under `governance` in `.exo/config.json` and run `exo sync`. `--no-verify` skips them once; CI still runs `exo check`.

## exo check

**``no fitness-assessment.json: ... the tier is unknown and Tier 4 rules apply; run `exo fitness classify --change <change>` ``**
The change was never classified, so the strictest rules apply. Ask your agent to classify it (the `risk-tiering` skill) or run the command in the message.

**`Tier N requires <artifact>`**
The change's tier requires an artifact it does not have yet (for example `test-spec.md` from Tier 2). Run the missing phase, for example with `/sdd-continue`.

**`the gate <gate> is ...: it needs the tech_lead role's approval in the PR`**
A gate that is not APPROVED, or that asks for approval, needs a person with the `tech_lead` role (`governance.roles` in `.exo/config.json`) to approve the pull request.

**`<base> and <head> have no common history; pass the branch the PR goes to`**
In CI this usually means a shallow clone. Fetch the full history (`fetch-depth: 0` in GitHub Actions) and pass the target branch, for example `exo check --base origin/main`.

## Publishing gates

**`review.publish_command is not approved on this machine for <project>:`** followed by the command and the project files it names
`exo gate publish` runs `review.publish_command` from the project's config in a shell, once per gate, and the config and the scripts can come from someone else's branch. So it runs only after you approve it on your machine, for that project. The approval covers the exact text of the command and the current content of the project files it names (such as `scripts/publish-gate.sh`). Read the command and those files; if you trust them, answer yes when `exo gate publish` asks in a terminal, or approve exactly that text with `exo gate publish --approve-command '<the command>'`. A different command (even by one space), another project or a change to one of those files asks again. The approval is kept in your user data folder, never in the repo, and an agent should ask you to run it rather than approve it itself.

**`review.publish_command was approved on this machine for <project>, but files it names changed since: <files>`**
Someone changed a script the command runs, for example a branch you checked out. Read the files the message lists before you approve the command again.

**`An earlier exo approved this text for every project and without the files it runs; approve it again.`**
An earlier version of exo approved only the text of the command, for every project. Approve it again in each project; the file of approvals is then rewritten in the new format.

**`--approve-command does not match review.publish_command; nothing was approved or run.`**
The text you passed is not the command in the config; the message prints the configured one. Approve only the command you read. In CI, this stops a branch that changes `review.publish_command`: it no longer matches the command the pipeline approves, and nothing runs. It does not stop a branch that changes the script the command runs, or the pipeline itself: publish from a pipeline whose definition and scripts come from a trusted ref (section D of `.exo/shared/ci-and-review.md`).

**`--approve-command was given, but review.publish_command is not set in .exo/config.json`**
There is no command to approve. Without one, `exo gate publish` prints the texts; set it with `exo init --publish-command "<command>"` or in the config.

**`.../approved-commands.json: not valid JSON (...); delete it to approve the commands again`**
The file of approved commands in your user data folder is damaged. Delete it and approve the command again.

**`.../approved-commands.json was written by a newer exo (schema N; ...); upgrade exo to use its approvals`**
A newer exo on this machine saved approvals in a format this one does not read. Upgrade exo (run the installer again); the file is left as it is.

## Memory

**`this Python lacks FTS5: lexical search ranks results in Python and is slower`** (`exo doctor`, line `memory-fts5`)
Use a Python from python.org or one managed by uv, and reinstall exo with it.

**`lexical search only`** (`exo doctor`, line `memory-semantic`)
Not an error. For hybrid search, install the `[vector]` extra (run the installer again with `--with-vector`, or `-WithVector` in PowerShell), then `exo mem model pull` and `exo mem reindex --provider local`.

**`sqlite-vec does not load in this Python (the extra is missing or this Python does not allow SQLite extensions), so semantic search runs in Python and is slow`**
Common with the Python that comes with macOS, which cannot load SQLite extensions. Search still works; for speed, install exo with a Python from python.org or uv.

**``model ... is missing; download it with `exo mem model pull onnx` ``**
Models are never downloaded on their own. Run the command in the message.

**`openai-compatible is remote: it needs --allow-remote`** and **`OLLAMA_HOST points to ..., which is not this machine`**
A remote embeddings provider would send your memory's text off your machine, so it needs your explicit `--allow-remote` on `exo mem reindex`.

**`EXO_EMBEDDINGS_URL must be an https:// URL (http:// only for this machine)`**
The API key travels with every request, so a remote endpoint must use `https`. Plain `http` is accepted only for `localhost`.

**`... answered with a redirect (...) to ...; redirects are not followed, so the key and the memory text never reach another address: point the URL at the final address`**
exo does not follow redirects of an embeddings endpoint. Set `EXO_EMBEDDINGS_URL` to the address the message names, if you trust it.

**``... can be read by other users (mode 755); it holds your memory, unredacted: run `chmod 700 ...` ``** (`exo doctor`, line `data-dir`)
On Linux and macOS, exo creates its data folder readable only by you, but it does not change a folder that already existed. Run the `chmod` in the message.

## Persona

**``<path>: ...; run `exo persona clear` and set it again with `exo persona set <role>` ``**
The file that stores your role is damaged. Clear it and set it again.

**``overlay: .exo/shared/personas/<role>.md is not installed in this project; run `exo sync` ``**
The project was installed with a version of exo without personas. Run `exo sync`, or `exo update` to see first everything the new version changes, then `exo update --apply`.

## The console

**`the console uses cp1252; some characters may display incorrectly. --json output is always UTF-8.`**
A Windows console with a legacy code page. Use Windows Terminal or run `chcp 65001`; output piped to a file or another program is UTF-8 already.

## Environment variables

| Variable | Effect |
|---|---|
| `EXO_DATA_DIR` | Your user data folder: memory, persona, approved publish commands, uninstall backups and the installer's virtual environment. By default `%LOCALAPPDATA%\exo-harness` on Windows, `~/Library/Application Support/exo-harness` on macOS and `~/.local/share/exo-harness` on Linux |
| `EXO_MEMORY_DB` | The memory database file (by default `memory.db` in the data folder) |
| `EXO_HOOK_CMD` | The command the git hooks run instead of the `exo` they find on the `PATH` |
| `EXO_CONTENT_ROOT` | A content tree to use instead of the one inside the package (for developing packs) |
| `EXO_EMBEDDINGS_URL`, `EXO_EMBEDDINGS_API_KEY` | The endpoint and key of the `openai-compatible` embeddings provider |
| `EXO_REF`, `EXO_REPO_URL` | Installers: the tag, branch or commit, and the repository to install from |
| `EXO_INSTALL_NO_PATH=1`, `EXO_INSTALL_NO_UV=1` | Installers: leave the `PATH` alone; do not use uv |

## Still stuck

Open an issue at https://github.com/julimonte03/exo-harness/issues with the output of `exo doctor --json` and the command that failed. Remove anything private from it first.
