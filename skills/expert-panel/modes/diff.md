# Mode: diff review

Examination of changes before a commit or merge request.

## Preflight

1. Make sure the current directory is inside a git repository: `git rev-parse --git-dir`. Not a repository — report and stop.
2. Parse the arguments. First extract `--spec <path>` together with its value — only the remaining positional argument counts as the base.
   - `--spec` is given but there is no file at the path — report and ask for a path. Do not continue silently: checking against the spec is half the point of the call.
   - A base remains — resolve it per step 3.
   - No base — compare the working tree with `HEAD`, skip step 3.
3. Resolve the base to a ref and check freshness. None of the commands is assumed to succeed — check each one:

       git rev-parse --verify <база>
       git remote get-url origin

   - No local ref, but `origin/<база>` exists — review against `origin/<база>` and tell the user.
   - Neither a local ref nor `origin/<база>` — report that the base was not found and stop.
   - `origin` is absent — skip the freshness check, warn that the base was not compared with the remote, and continue. A repository without a remote is a normal case, not an error.
   - A local ref exists but `origin/<база>` does not — the base is a tag, a SHA or a branch without upstream. Skip the freshness check, say so and continue.
   - `origin` and both refs exist — run:

         git fetch origin <база> --quiet
         git rev-list --count <база>..origin/<база>

     A result greater than zero means the local base is behind. Ask the user: update the base or review against the stale one. Silently reviewing the wrong diff is worse than not reviewing at all.
4. Collect the list of changed files (`git diff --name-only` with the same base as in step 5) and apply the filters from the «File filtering» section — before obtaining the diff, not after. A filter applied to the report but not to the diff is a lie to the user: the agents will still read the excluded files and refer to them.
5. Obtain the diff limited to the remaining paths and save it to a temporary file — agents receive the path, not the content in the prompt:
   - without a base: `git diff HEAD -- <оставшиеся пути>`;
   - with a base: `git diff <разрешённая база>...HEAD -- <оставшиеся пути>` — three dots, comparison from the divergence point. Uncommitted changes do not get in here; if the working tree is dirty, tell the user.

   **If no path remains after filtering — do not obtain a diff at all.** An empty pathspec means «everything» to git, and the command returns the full unfiltered diff including `vendor/` and generated code that the report will call «исключено». Leave the diff empty and continue only with the untracked files from step 6.
6. **Untracked files.** `git diff` does not see them in any variant, and before a commit a new file is the most common kind of change. Get them as a list:

       git status --porcelain

   Show the user the lines with status `??` and ask: include in the review or skip. Included ones are passed to the agents as a separate list of paths — the agents read such a file in full, not as a diff. Apply the filters from the next section to them too. Do not touch the index: `git add -N` is a write, and the skill writes nothing before the user's consent.
7. If neither tracked changes after filtering nor included untracked files remain — report and stop. This cannot be checked before step 6: a working tree whose only change is a new file would otherwise end with «нет изменений» in exactly the scenario step 6 exists for.

## File filtering

Filters are applied to the file lists before the content reaches the agents: to tracked files at step 4, before obtaining the diff; to untracked files at step 6. Exclude three categories:

1. **Generated Go code** — files where a line of the form `// Code generated ... DO NOT EDIT.` appears before the first non-empty non-comment line. Not necessarily the first line of the file: a license header and `//go:build` may be above it.
2. **Default path list:** `vendor/`, `*.pb.go`, `*_mock.go`, `testdata/`.
3. **Project list.** First check `.kirpr/expert-panel-ignore`.
   - The file exists — read it: every non-empty line not starting with `#` is treated as a pattern.
   - The file does not exist and neither does `.claude/expert-panel-ignore` — there is no project list.
   - No new file, but the legacy `.claude/expert-panel-ignore` exists — show the user both paths and ask whether to copy the legacy file to `.kirpr/expert-panel-ignore`. Until answered, the legacy file is only read. On consent copy it once and read the new file from then on; on refusal read the legacy file without writing it.

   Every team has its own set of generators; this is a property of the project, not of the skill.

Pattern semantics are the same in both lists: the path is taken from the repository root; a pattern with a trailing `/` is a directory prefix; otherwise a regular glob over the whole path, so `*.pb.go` matches at any depth.

Show the user how many files were excluded and why. Silent exclusion reads as «панель это посмотрела».

## Phase 1. Context

1. The list of changed files with statistics and the list of included untracked files.
2. For every file in the diff, read the context in full, not only the changed lines. Only the diff is reviewed, but it cannot be judged without its surroundings. Untracked files are read in full — they have no «changed lines», the whole file is new.
3. If `--spec <path>` was passed — read the spec and its `## Review log`.
4. Show a summary: the base and how it was resolved, the number of files, excluded files with reasons, the fate of untracked files, whether a spec is present.

**Do not move to Phase 2 without the user's confirmation.** This is the only moment to fix the base or the exclusion list before launching N parallel agents.

## Phase 2. Panel

Assemble the active panel and launch the agents per the protocol in `SKILL.md`. Mode — `diff`: the agent uses the «В diff проверяет» block of its persona.

Pass to every agent: the path to the diff file, the list of changed files, the list of included untracked files marked «читать целиком», the spec path and its Review log if `--spec` was passed.

If the diff is empty because all changes are in untracked files, tell the agent so directly. Otherwise it will decide it was given broken input and return an empty result.

With `--spec`, every agent additionally checks:
- what from the spec is not implemented;
- what was done beyond the spec;
- which decisions recorded in the Review log are violated.

## Phase 3. Report

Synthesize per the protocol in `SKILL.md`. Every finding must have `file:line`.

1. **Панель** — who took part, the base, the number of files.
2. **Удачные решения** — mandatory if there is anything to name. A report made only of complaints stops being read.
3. **Замечания** — by descending severity.
4. **Конфликты**.
5. **Ниже порога**.
6. **Что не смотрели** — excluded files, skipped untracked files, everything that did not make it into the diff. The verdict carries weight, and it must not be issued over an undeclared blind spot.
7. **Вердикт** — `Approve`, `Approve with comments` or `Request changes`. With `Request changes`, list the blockers.

## Phase 4. Walkthrough

The same format as in spec mode:

    accept C2,S1; reject F3 — причина; ? P4

## Phase 5. Edits

1. Apply only the accepted findings.
2. Do not run tests, linters or builds — print the commands for the user to run. The panel judges the code; it is not responsible for it building.
3. Show the diff of the edits made.
4. Do not commit.
