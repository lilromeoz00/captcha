# UPLOAD INSTRUCTIONS — read this once

You have three things in `C:\Users\Jordan\Downloads\`:

| item | what it is | use it if |
|---|---|---|
| `cs471-checkpoint-upload\` | the repo **with** `.git` (has the `checkpoint` tag) | you're comfortable with 4 git commands → **do this one** |
| `cs471-checkpoint-webupload\` | same files, **no** `.git` folder | you want to drag-and-drop into github.com in a browser |
| `cs471-checkpoint.zip` | a zip of the first folder, for backup/safe-keeping | you want a copy to keep |

---

## Option A — git push (RECOMMENDED: this is the only way the `checkpoint` TAG gets uploaded)

The assignment explicitly asks for *"a link to your GitHub repository with the
checkpoint tag identifying the submitted version."* A tag only exists in git, so
web-drag-and-drop **cannot** satisfy that requirement. Use this option.

1. Create an empty repo on github.com. **Name it something like `cs471-adversarial-vision`.**
   Do NOT add a README, .gitignore, or license — leave it completely empty.
2. Open PowerShell and paste these four lines, replacing `YOURNAME` and `REPO`:

```powershell
cd C:\Users\Jordan\Downloads\cs471-checkpoint-upload
git remote add origin https://github.com/YOURNAME/REPO.git
git push -u origin main
git push origin checkpoint
```

3. On github.com go to your repo → the branch/tag dropdown (says `main`) → **Tags** →
   `checkpoint` should be listed. Click it, then click **"Create release from tag"**
   if you want it to be obvious to your instructor.
4. Repo **Settings** → scroll to the bottom → **Change visibility** → **Public**.
   (Required: "Your instructor must have access to the repository.")

When git asks for a password, it will not accept your GitHub password. Use a
**Personal Access Token**: github.com → Settings → Developer settings →
Personal access tokens → Tokens (classic) → Generate new token → check `repo` →
copy it and paste it as the password.

---

## Option B — drag and drop in the browser (only if git is fighting you)

1. Create an empty public repo on github.com.
2. Open `C:\Users\Jordan\Downloads\cs471-checkpoint-webupload\`
3. Select **all** files and folders inside it (Ctrl+A), drag them onto the GitHub
   "uploading an existing file" page, commit.
4. You will then need to create the tag by hand: on the repo page click
   **Releases** → **Create a new release** → "Choose a tag" → type `checkpoint` →
   "Create new tag on publish" → publish. This is the manual equivalent of the tag.

⚠️ Do not drag the `-upload` folder (the one with `.git`); GitHub's web uploader
will choke on it. Use `-webupload`.

---

## After uploading — the Blackboard submission

Two things go in the Blackboard text box:

1. The repo link: `https://github.com/YOURNAME/REPO/tree/checkpoint`
   (linking the *tag*, not `main`, so the instructor sees exactly what you submitted)
2. The contents of **`CHECKPOINT_SUMMARY.md`** — that's your 150–250 word progress
   summary, already written, covering completed functionality, remaining work, and
   per-member contributions.

Before you submit, check that `CHECKPOINT_SUMMARY.md` and `PROGRESS.md` name you as
the sole author (this is a solo submission, so the contribution split is 100% / 0%).
Those files are already filled in correctly.

---

## Sanity check (optional, 10 seconds)

```powershell
cd C:\Users\Jordan\Downloads\cs471-checkpoint-upload
python tests\run_all.py
```

Should print `ran 48 ... PASS`. It already did when I made this folder.
