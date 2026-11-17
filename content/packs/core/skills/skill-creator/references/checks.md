# Checks

What step 10 of `skill-creator` checks: the rules `exo validate` enforces on a content tree, what each message means and how to fix it, and the same checks by hand for a project skill, where `exo validate` does not apply.

## exo validate

Run it from the engine's repository as `exo validate --root content` (without `--root` it validates the content packaged with the installed exo, not your working tree), or on any content tree with `packs/` and `rules/` (`exo validate --root <tree>`). Add `--json` to process the result. The exit code counts only errors; read the warnings too: a new skill should add none.

| Rule | Message (abridged) | Fix |
|---|---|---|
| Only standard fields at the top level | `field 'X' is not part of the Agent Skills standard; move it to metadata with the engine prefix` | Move it under `metadata`, as `exo-<key>` |
| Name equals the folder | `name must match the folder name ('a'), not 'b'` | Rename one of them |
| Name format | `name '...' must be kebab-case: a-z, 0-9 and single hyphens` | Lowercase, digits, single hyphens |
| Name length | `name has N characters; the maximum is 64` | Shorten it |
| Description present | `missing description (with triggers in English)` | Write it (`references/description-and-triggers.md`) |
| Description length | `description has N characters; the maximum is 1024` | Cut adjectives and second examples |
| Metadata values | `metadata.<key> must be a string, not ...` | Quote numbers and booleans |
| Size (warning) | `SKILL.md has N lines, more than 500 lines; move the details to references/` | Move detail to a reference |
| Escapes | `literal Unicode escape ...: write the character directly` | Type the character itself |
| Cited references exist | `cites references/<file>, which does not exist` | Create the file, or fix the path |
| `skill:` references resolve | `skill:<name> belongs to pack P, which Q does not declare in requires or optional` | Use backticks with the pack and the degradation sentence, or declare the pack in `pack.json` if it really is a dependency |
| Unknown skill | `skill:<name> is not in the collection; ...` | Fix the name, or write it in backticks |
| Shared contracts reachable | `cites <engine folder>/shared/<file>, which ships in pack P; pack Q does not require it ...` | Cite only contracts of the pack or of packs it requires |
| Unique names | `duplicate skill name: <name> (packs ...)` | Rename the new skill |
| Secrets (outside code blocks) | `possible secret (<kind>): ...` | Replace it with a `<placeholder>`; if it was real, tell the owner to rotate it |
| Suspicious instructions (warning) | `suspicious instruction (<kind>): found ...` | Remove it; a skill that only describes an attack describes it without the literal phrase |

The suspicious-instruction pre-check looks at every line, code blocks included, for: text that overrides the agent's instructions or hides things from the person; downloading and running code in one step; sending data to a non-local address; asking the person for credentials or identity documents; and invisible characters (zero-width, bidirectional controls, tag characters).

## Manual checks for a project skill

`exo validate` validates content trees, not a loose skills folder. Run these instead, from the project root (POSIX shell; adapt the commands in PowerShell):

1. **Frontmatter:** the file starts with `---`, the block closes with `---`, and it has only standard top-level keys (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`).
2. **Name equals the folder,** kebab-case, up to 64 characters.
3. **Description** up to 1024 characters, with `Use it when` and `Triggers:`.
4. **Size:**

   ```sh
   wc -l .claude/skills/<name>/SKILL.md
   ```

5. **Every cited reference exists:**

   ```sh
   grep -o 'references/[A-Za-z0-9._-]*' .claude/skills/<name>/SKILL.md | sort -u
   ls .claude/skills/<name>/references/
   ```

6. **No invisible characters** (ripgrep):

   ```sh
   rg -n '[\x{200B}-\x{200F}\x{202A}-\x{202E}\x{2066}-\x{2069}]' .claude/skills/<name>/
   ```

7. **No secrets or personal data:** in a project with the engine, `exo check --base <target branch>` scans the lines the branch adds, and the `pre-commit` hook scans staged lines.
8. **No name clash** with the engine's skills: `exo skills list`.

## The review gate

After the checks, run `skill-reviewer` on the new folder. It reads every file raw, triages the warnings and returns `APPROVED` or `ESCALATED` with a findings table. Put its verdict in the pull request. An `ESCALATED` skill needs the `tech_lead` role before it is merged.

## Common mistakes

| Mistake | What happens | Fix |
|---|---|---|
| A description that lists everything the skill touches | It loads on unrelated requests | Keep the situations where it is the right skill |
| Steps without a stop condition | The agent improvises when something fails | Say: ask once, stop with `needs-input`, or degrade |
| A long example in `SKILL.md` | The file passes 300 lines and hides the steps | Keep a short excerpt; the full example in a reference |
| `skill:` to a skill of a pack not declared | Validation error, and a broken link when that pack is missing | Backticks, the pack name and the degradation sentence |
| Real data in an example | A scanner error, or a data leak | Placeholders and synthetic values |
| Writing into an SDD artifact from a non-phase skill | Breaks artifact ownership | Return the text to the phase that owns the artifact |
