# Toolchain and manual review

Commands for each step of the chain in `security-scan-node`, and the manual checks of manifests and lockfiles. Run only tools the project already has; never install one, never run a command that writes files in the repository.

## Step 1: the package manager's audit

| Manager | Production only | Full tree | Why is a package here | Needs |
|---|---|---|---|---|
| npm | `npm audit --omit=dev --json` | `npm audit --json` | `npm explain <package>` | `package-lock.json` or `npm-shrinkwrap.json` (otherwise it stops with `ENOLOCK`) |
| pnpm | `pnpm audit --prod --json` | `pnpm audit --json` | `pnpm why <package>` | `pnpm-lock.yaml` |
| Yarn 2 and later | `yarn npm audit --all --recursive --environment production --json` | `yarn npm audit --all --recursive --json` | `yarn why <package>` | `yarn.lock` |
| Yarn 1 | `yarn audit --groups dependencies --json` | `yarn audit --json` | `yarn why <package>` | `yarn.lock` |
| Bun | `bun audit --prod --json` | `bun audit --json` | `bun pm ls` | `bun.lock` |

- In a workspace monorepo, run at the root: the root lockfile covers every workspace. `npm audit --workspace <name>` narrows the report to one.
- `--audit-level=high` changes only the exit code, not what is reported; read the whole JSON.
- `npm audit signatures` verifies registry signatures and provenance of installed packages; it needs `node_modules`. Report unsigned or invalid packages as CWE-494, A08:2025.
- **Never** `npm audit fix`, `npm install`, `npm update` or `npm install --package-lock-only`: they change the repository. Give them to the person as next steps.

## Step 2: OSV-Scanner

| Version | Whole repository | One lockfile | Output |
|---|---|---|---|
| 2.x | `osv-scanner scan -r .` | `osv-scanner scan -L package-lock.json` | `--format json` |
| 1.x | `osv-scanner -r .` | `osv-scanner --lockfile=package-lock.json` | `--format json` |

It reads every lockfile it finds, Node and others, and reports OSV IDs with their GHSA and CVE aliases. An `osv-scanner.toml` in the repository may ignore some IDs on purpose: list the ignored IDs and their reasons in the report. Offline, `--offline-vulnerabilities` checks against local databases that are already cached; never add `--download-offline-databases` in a build that must stay offline.

## Step 3: OWASP dependency-check

```text
dependency-check --project <name> --scan . --format JSON --out <temporary folder outside the repository>
```

- It analyzes `package-lock.json` (and `yarn.lock` or `pnpm-lock.yaml`) and matches packages against the NVD and other sources. It needs its vulnerability data already downloaded or mirrored by the project's setup; without it, skip the step and say why.
- Its report goes to a folder outside the repository, so the working tree stays clean.
- It reports CPE-based matches, which can be false positives on packages with common names: check the package name and ecosystem before reporting one.

## Optional: SonarQube and Fortify

- Only when the project already has them: a `sonar-project.properties`, a scanner step in CI, a Fortify or ScanCentral job.
- Read the results the way the project already does (the CI job's report, the server's page for the branch). Never configure them, never create tokens, never upload code to a server the project does not already use.
- Their findings join the report with their source; their absence is not a finding.

## Manual review

Always, also when the tools ran. Each check names its CWE; the OWASP Top 10:2025 category comes from it through `.exo/shared/owasp-2025.md` (all of them are `A03:2025` except LOCK-4, `A08:2025`, and `strict-ssl=false` in LOCK-7, `A07:2025`).

| ID | What | Signal | Severity | CWE |
|---|---|---|---|---|
| LOCK-1 | No lockfile, or a manifest changed without its lockfile | `package.json` in the diff without the lockfile; no lockfile in the repository | Medium; High when CI or the Dockerfile installs from it into production | CWE-1357 |
| LOCK-2 | Loose or risky version spec | `*`, `latest`, `>=` with no upper bound, `x` ranges for new dependencies; `git+`, `github:`, tarball URLs, `file:` outside the repository | Medium | CWE-1357 |
| LOCK-3 | Unexpected source | `resolved` to a host other than the project's registry, or over `http://` | High | CWE-1357 |
| LOCK-4 | Integrity changed for the same version | `integrity` of `name@version` differs from the base branch | Critical: stop and tell the person (possible tampering) | CWE-494 |
| LOCK-5 | New install scripts | `preinstall`, `install` or `postinstall` added to the project's scripts; `hasInstallScript: true` on a new package in `package-lock.json` | Medium; High for a new, little-known package | CWE-1357 |
| LOCK-6 | Possible typosquat or dependency confusion | A name one character away from a popular package; an internal scope (`@company/`) resolved from the public registry; a brand-new package with a handful of downloads | High, as `Unconfirmed:` | CWE-1357 |
| LOCK-7 | Registry or TLS settings changed | `.npmrc` with a new `registry`, `strict-ssl=false`, `ignore-scripts=false` where it was true | High | CWE-1357 for a new registry or scripts turned back on; CWE-295 for `strict-ssl=false` |
| LOCK-8 | Overrides that pin or downgrade | `overrides`, `resolutions` or `pnpm.overrides` added or changed | Medium: check the pinned version is not vulnerable | CWE-1395 |
| LOCK-9 | A dev tool moved to production | A package moved from `devDependencies` to `dependencies` | Low; Medium if it has known advisories | CWE-1357 |
| LOCK-10 | Unmaintained dependency | A new dependency that is deprecated or archived, or whose last release is years old | Low to Medium | CWE-1104 |

### Versions you recognize

When a manifest pins a version you know to be vulnerable and no tool could confirm it, report it as a `DEP-n` finding that starts with `Unconfirmed:`, with the advisory you recall, the first fixed version you recall, and the command that would confirm it (`npm audit --omit=dev`, or `osv-scanner` on the lockfile). Your memory can be outdated or wrong; the person must be able to tell a recalled finding from a scanned one.
