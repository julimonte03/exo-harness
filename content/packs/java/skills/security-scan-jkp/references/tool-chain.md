# The open scanning chain

Run only what the project already has. Each tool below downloads advisory data; run it where the project already does (CI) or where the person allows network access. Configuration such as an NVD API key lives in the project's own settings or environment, never in the conversation.

## Step 1: native audit

### OWASP dependency-check, Maven plugin

- **Present when** `pom.xml` declares `org.owasp:dependency-check-maven` (in `<build><plugins>` or a profile).
- **Run:** `./mvnw -B org.owasp:dependency-check-maven:check` (one module) or `...:aggregate` (multi-module). Add `-Dformat=JSON` for a machine-readable report next to the HTML one.
- **Report:** `target/dependency-check-report.html` and `.json`.
- **Note:** the plugin may fail the build on purpose when a score passes `failBuildOnCVSS`. That is a result, not an error: read the report.

### OWASP dependency-check, Gradle plugin

- **Present when** the build applies `org.owasp.dependencycheck`.
- **Run:** `./gradlew dependencyCheckAnalyze` (or `dependencyCheckAggregate` for multi-project builds).
- **Report:** `build/reports/dependency-check-report.html` (and JSON when configured).

### pip-audit (Python)

- **Present when** `pip-audit` is on the path or in the project's dev dependencies.
- **What `-r` does:** `pip-audit -r <file>` is close to `pip install -r <file>` in a temporary virtual environment. It downloads every package, resolves the transitive ones, and may build a source distribution, which runs that package's build code on this machine. Never run it that way here.
- **Run, safely:**
  - `pip-audit --format json` with no input, inside the project's environment that is already installed (the activated virtual environment, `uv run pip-audit`, `poetry run pip-audit`): it audits what is installed and installs nothing.
  - `pip-audit -r <file> --no-deps --disable-pip --format json`, only when every line of the file is pinned with `==` (and better, with `--hash`, which also makes pip-audit check each hash): it reads the pins without resolving or installing.
  - Loose requirements (`>=`, no pin) and no environment: do not audit them with pip-audit. Run OSV-Scanner, or report the step as not run with the command for the person, and report the loose pins as `LOCK-n`.
- **Lockfiles of Poetry, uv or PDM:** go straight to OSV-Scanner, which reads them. Exporting them to a requirements file only helps when the export is pinned and hashed, and it goes to a folder outside the repository.
- **Exit code 1** means vulnerabilities were found.

## Step 2: OSV-Scanner

- **Present when** `osv-scanner` is on the path.
- **Run (v2):** `osv-scanner scan source -r .`, or `osv-scanner scan source -L <lockfile>` for one file; `--format json` for parsing. Version 1 uses `osv-scanner -r .`.
- **Reads:** `pom.xml` (resolving transitive dependencies from the Maven repository), `gradle.lockfile`, `buildscript-gradle.lockfile`, `requirements.txt`, `poetry.lock`, `uv.lock`, `pdm.lock`, `Pipfile.lock`, among others, without installing anything. A Gradle build without lockfiles has nothing for it to read: say so.
- **Sends** package names and versions to the OSV service, never source code.
- **Exit code 1** means vulnerabilities were found.

## Step 3: OWASP dependency-check CLI

- **Present when** `dependency-check` (or `dependency-check.sh`, `dependency-check.bat`) is on the path.
- **Run:** `dependency-check --project <name> --scan <path> --format JSON --out <folder outside the repository>`. Python analyzers need `--enableExperimental`.
- **Note:** the first run downloads the NVD data and is slow. It matches libraries by CPE, which produces false positives for products with similar names: check the package coordinates before reporting.

## Optional: SonarQube and Fortify

- **SonarQube:** only when the project already has it (`sonar-project.properties`, the `sonar-maven-plugin` or the `org.sonarqube` Gradle plugin, a Sonar step in CI). Prefer reading the issues and the quality gate that CI already produced. Running `sonar:sonar` uploads the code to the server: only when the project does it already and the person asks.
- **Fortify:** only when the project has its configuration (a `sourceanalyzer` step in CI, Fortify SSC settings). Read the results CI produced.
- Neither replaces steps 1 to 3, and their absence is never a finding.

## What to take from each result

For every vulnerable package: the coordinates (`group:artifact` or the PyPI name), the version, the advisory IDs (CVE, GHSA, PYSEC), the CVSS score and severity, the fixed versions, and whether it is direct or transitive (the dependency path: `mvn dependency:tree -Dincludes=<group>:<artifact>`, `./gradlew dependencyInsight --dependency <artifact>`, `pip show` or `pipdeptree`).

## Fixing (as text, never applied by this skill)

- **Direct dependency:** upgrade to the fixed version. In Spring Boot, a library the BOM manages is upgraded through its property (`<log4j2.version>`, `<snakeyaml.version>`) or by removing an explicit version that pins it below the BOM.
- **Transitive dependency:** upgrade the direct dependency that brings it; or set the version in `dependencyManagement` (Maven) or a `constraints {}` block (Gradle); exclusion only when the library is not needed.
- **Python:** raise the pin in the requirements or `pyproject.toml`, and regenerate the lockfile with the project's tool.
- **No fix released:** say so, and propose a mitigation (avoid the vulnerable API, a configuration switch the advisory names).

## Manual review when no tool runs

Report only advisories you know with certainty, with `manual, not confirmed by a scanner`. Well-known examples for Java:

| Package | Affected | Advisory | Fixed | Reachable when |
|---|---|---|---|---|
| `org.apache.logging.log4j:log4j-core` | 2.0-beta9 up to 2.14.1 | CVE-2021-44228 (Log4Shell), Critical | 2.15.0; use 2.17.1 or later for the follow-up CVEs | any logged string that contains user input (message or parameters) |
| `org.springframework:spring-beans` (Spring Framework) | 5.3.0 to 5.3.17, 5.2.0 to 5.2.19 | CVE-2022-22965 (Spring4Shell), Critical | 5.3.18, 5.2.20 | data binding to plain objects, on JDK 9+, deployed as a WAR on Tomcat |
| `org.apache.commons:commons-text` | 1.5 to 1.9 | CVE-2022-42889 (Text4Shell), Critical | 1.10.0 | `StringSubstitutor.createInterpolator()` or the default lookups applied to untrusted input |
| `org.yaml:snakeyaml` | before 2.0 | CVE-2022-1471, Critical in NVD | 2.0 | `new Yaml()` or `Constructor` loading untrusted YAML |

Anything else: list the package and version as `not checked: run a scanner`. Never guess a CVE from a version number.
