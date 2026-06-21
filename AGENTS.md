# Project Conventions

## Communication Style
- You should address me as 'sir' in EACH response you sent to me

## Git Conventions
- git fetch often
- Use dedicated branch for new features/new bug fix exercise with git commit'ing/git push'ing, git pull/git rebase before each sprint of work
- Don't mention the identity of contributor/author/co-author in commit/PR messages -- reviewers should evaluate the code on its own.
- Write short commit messages, at most two lines long

## Code Comments (incl. docstring)
- Do not add excessive comments. Comments become stale fast; try to express the intention with code. Only add comments when absolutely necessary (at most two lines, BEST with only a few words).
- Remove excessive comments in the code you modify.

## AI Workflow
- Never modify or rewrite this `AGENTS.md` file. It is a read-only system constraint.
- Preference Tracking: When you learn a new developer preference, workflow habit, or project rule, do not just keep it in your internal context. Explicitly append it to the rules section of this CLAUDE.md file and prepend it with author name and date time.
- **Long-Term State Tracking:** You are required to track your long-term context, progress, and architectural decisions in the `MEMORY.md` file located at the project root. 
    - **At Session Startup:** Read `MEMORY.md` to understand your current objectives, recent changes, and outstanding tasks.
    - **At Session Wrap-up / Checkpoints:** Update `MEMORY.md` using your file-editing tools. Log what you accomplished, what broke, and what the next developer session should focus on.
    - **Structure & Style:** Keep `MEMORY.md` clean, concise, and split strictly into two distinct Markdown zones:
        - *Active Status (Top of File):* An undated, high-level summary of the live objective and immediate next steps. Overwrite this text frequently to keep it current.
        - *Chronological Activity Log (Bottom of File):* Append a fresh entry here for every milestone or session wrap-up. You **must** prepend the exact date in `YYYY-MM-DD` format to the entry header and arrange them in reverse chronological order (newest entries at the top of this section).
    - **Automatic Pruning:** To protect the context window from bloating, if the Chronological Activity Log in `MEMORY.md` exceeds 5 entries, automatically extract the oldest entries and append them to a `MEMORY_ARCHIVE.md` file at the project root.