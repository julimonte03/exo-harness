# toy-todo

A tiny to-do list, stdlib only. It is the toy project for trying the SDD
cycle by hand: copy it to a temporary folder, `git init`, and adopt the engine there.

```bash
python -m toy_todo add "buy milk"
python -m toy_todo list
python -m toy_todo done 1
```

Tasks are stored in `tasks.json` (or the file in `TOY_TODO_FILE`).

Tests: `python -m pytest` (needs pytest).
