# Data protection contract

What data may go where. It applies to every skill and to the agent outside any skill. The `data-classification` skill (pack `security`) applies it step by step; without that skill, apply this contract inline.

## A. Levels

| Level | What it is | Examples |
|---|---|---|
| Public | Already published, or meant to be | Open-source code, public docs |
| Internal | The organization's own, not personal and not secret | Architecture, internal service names, non-secret config |
| Restricted | Personal data (PII) of real people | Card numbers, IBANs, national ID numbers, personal emails and phone numbers |
| Critical | Credentials and secrets | Passwords, API keys, tokens, private keys, connection strings with a password |

When in doubt between two levels, take the higher one.

## B. Destinations

- **Memory:** `exo mem` and any other persistent memory.
- **Model:** prompts, briefs for subagents, the conversation and your answers.
- **Repository:** code, tests, fixtures, specs, commits and PR descriptions.
- **External systems:** trackers, chat, PR comments, web tools and any MCP server that leaves the machine.

## C. The matrix

| Level | Memory | Model | Repository | External systems |
|---|---|---|---|---|
| Public | allowed | allowed | allowed | allowed |
| Internal | allowed | allowed | allowed | only the organization's own systems |
| Restricted | blocked | blocked unless a waiver covers it | blocked unless a waiver covers it | blocked unless a waiver covers it |
| Critical | forbidden | forbidden | forbidden | forbidden |

- **Critical has no waiver.** If a credential shows up in code, a log or a prompt, do not copy it anywhere: point at `path:line`, tell the person to remove it and to rotate it if it was real.
- **Restricted that you read** (in code, a database dump, a log): do not repeat it. Mask it in your answer (`****1234`) and refer to it by location.
- **Memory has no waiver either:** it does not filter and it can be exported.
- **Test data is synthetic:** published test card numbers, `example.com` addresses, placeholders such as `<your-password>` or `${DB_PASSWORD}`. The scanner ignores them. Generated IDs with a valid check digit count as personal data: they need a waiver for their fixture folder.

## D. What the engine enforces

The same scanner runs in the `pre-commit` git hook (staged lines), in `exo check --base <target>` (lines the branch adds, and new files; `exo check --change` alone does not scan) and in `exo validate` (the engine's own content, Critical detectors only, outside code blocks).

- **Critical detectors, always on:** AWS keys, GitHub tokens, private keys, Slack tokens, credential assignments, unquoted `.env` assignments, JWTs, URLs with a password, connection strings and Azure DevOps tokens.
- **Restricted detectors:** the ones in `data_protection.pii` in `.exo/config.json`. The default is `card` (Luhn check) and `iban` (mod 97 check). The project can add `email`, `phone` and national documents: `ar-cuit`, `br-cpf` and `es-nif` with their check digit, `ar-dni` (next to the word DNI) and `us-ssn` (format only). Add only the ones its data can contain.
- **Files that never get committed,** whatever their case: `.env` and `.env.*` (except `.env.example`, `.env.sample` and `.env.template`), private keys and keystores (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `*.ppk`, `id_rsa` and similar), and credential files (`.pypirc`, `.netrc`, `credentials.json`). The `pre-commit` hook blocks them, and reverse engineering lists them by name without reading them.

A blocked commit or check names the file, the line, the detector and a redacted excerpt. Fix the cause; never use `--no-verify` (CI runs the same scan).

## E. Waivers

A waiver is an approved, dated exception for **Restricted** data in specific paths. They live in `.exo/waivers.json`, which the person owns; its schema is `.exo/shared/schemas/waivers.schema.json`.

```json
{
  "waivers": [
    {
      "detector": "ar-cuit",
      "path": "tests/fixtures/**",
      "reason": "Generated CUITs with a valid check digit for the validator tests",
      "approved_by": "@tech-lead",
      "expires": "2027-06-30"
    }
  ]
}
```

- The `tech_lead` role approves it; an agent never adds or extends a waiver on its own.
- Keep the path as narrow as possible. An expired waiver no longer applies.
- There is no waiver for Critical: the schema does not accept those detectors.
