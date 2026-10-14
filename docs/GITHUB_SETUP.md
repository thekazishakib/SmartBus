# Put SmartBus on GitHub

Prepared for **Kazi Shakib** (`thekazishakib`). The suggested repository name is **SmartBus**. These files do not create or publish a remote repository by themselves.

## Create the repository

1. Sign in to GitHub and create a new repository named `SmartBus` (or choose your own name).
2. If using the commands below, leave GitHub's automatic README, `.gitignore` and license options unchecked; this package already includes them.
3. Choose the visibility you intend. The example data is fictional; real ledgers, workbooks and backups should stay local.
4. If you choose another repository name, update `project.json` and run `python tools/update_readme.py`.

Suggested description:

> Local bus trip and counter revenue reconciliation with Python, Excel, SQLite and printable reports.

Suggested topics: `python`, `excel`, `sqlite`, `finance`, `accounting`, `reconciliation`, `bus-management`, `automation`.

## Upload the extracted contents

### Browser upload without Git commands

1. Extract the final ZIP. Open the inner `SmartBus` folder; `README.md` should be directly inside it.
2. Open the new GitHub repository and choose the upload-existing-files link, or **Add file → Upload files**.
3. Drag the contents of the inner folder into the upload area, including `assets`, `docs`, `tools`, `.github`, `.gitignore` and `.gitattributes`. This package has fewer than 100 files and no file approaches the 25 MiB browser limit.
4. Check the displayed paths: `README.md` must be at the repository root, not `SmartBus/README.md` inside another folder. Check dot-prefixed files and both workflow files were included.
5. Use a commit message such as `Publish SmartBus v1.2.1` and finish GitHub's commit flow. If a branch or pull request is required, complete that flow before checking the default branch.
6. Confirm the source files and rendered README appear. Uploading only the ZIP does not create a browsable source repository.

Upload this clean extracted release before running it. Browser uploads do not apply `.gitignore` to filter selected files; do not drag a used working folder containing accounts or backups.

GitHub's [official file upload instructions](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository) describe the current interface and limits.

### Command-line alternative

Run these commands inside the extracted `SmartBus` folder after creating the empty repository:

```text
git init
git add .
git status
git commit -m "Initial SmartBus release"
git branch -M main
git remote add origin https://github.com/thekazishakib/SmartBus.git
git push -u origin main
```

Inspect `git status` before the commit. Keep `daily/` and `reports/` limited to `.gitkeep`; do not publish `data/`, `backups/`, `demo_workspace/` or real accounts. The supplied ignore rules and release packager exclude these locations.

Commit the source folder contents, including `.github/`, rather than uploading only an outer ZIP. The README images use relative paths and will appear after `assets/` is committed.

## Check CI

Open the repository's **Actions** tab after upload. The Tests workflow runs on pushes and pull requests. Local passing tests do not guarantee a remote job has completed; inspect the actual run.

## Prepare a release archive

```text
python -m unittest discover -s . -p "test_*.py" -v
python tools/package_release.py
```

The archive and SHA-256 checksum appear under `dist/`. The archive includes a per-file release manifest.

Alternatively, open **Actions → Build release archive → Run workflow** after upload and download its artifact. That workflow builds files only; it does not publish a GitHub release automatically.

## Publish a release when ready

In GitHub's **Releases**, draft a release with tag `v1.2.1`. Use the current release notes, attach the ZIP and checksum from `dist/`, and inspect the draft before publishing it. No tag or remote release has been created by this file-preparation task.

## License and attribution

The repository includes the MIT License, copyright 2026 Kazi Shakib, and explicit third-party notices. Keep both files in the source and release archive. The MIT License does not grant rights to redistribute Microsoft products or other external dependencies under MIT.

## After the first release

Read the [owner learning and showcase guide](OWNER_GUIDE.md). Confirm the source repository, Actions results, downloadable release and your ability to demonstrate the fictional account. Explain AI assistance and your contributions accurately. Publication is not evidence of professional Python proficiency or real-company adoption.
