# Desk Sorter

Sort thousands of pictures and videos on your Mac by looking at them, not by opening them one by one.

It shows every image and video in the folders you pick as one long page of thumbnails. You select a few, or a whole folder, press a number key, and they're in a bucket: a brand, a project, "Personal", "Delete?". When you're done, it shows where each bucket would go and moves the files only when you say so. Every move is logged and can be undone.

It runs on your Mac only. Nothing is uploaded, and no AI looks at your pictures.

I built it with Claude Code for my own Downloads folder: 4,784 images and videos in 94 folders, which no app sorted the way I think about my work. I sorted 3,500 of them in one evening.

## What you need

- A Mac. It uses the Mac's own `sips` and `qlmanage` for thumbnails.
- `python3`. Type it in Terminal. If it's missing, macOS offers to install it (the Command Line Tools).
- Nothing else: no packages, no account, no internet.

## Use it with Claude Code (easiest)

Install it as a skill:

```
git clone https://github.com/frederikeff/desk-sorter ~/.claude/skills/desk-sorter
```

Then tell Claude Code: "sort the pictures in my Downloads". Claude measures the folder, asks for your buckets, opens the page, and waits while you sort. Afterwards it shows you the plan and moves files only after your yes.

## Use it by hand

```
cd desk-sorter

# 1. Make the sheet. This only reads; nothing moves.
python3 make_sheet.py downloads ~/Downloads --buckets "Work,Personal,Content,Delete?,Not sure"

# 2. Sort on the page: http://127.0.0.1:8791
python3 server.py downloads

# 3. See the plan. This writes data/downloads/plan.json; nothing moves.
python3 apply.py downloads

# 4. Change the targets in plan.json if you like, then move.
python3 apply.py downloads --go

# Changed your mind?
python3 apply.py downloads --undo moves-<time>.tsv
```

Add `--all` to step 1 to take documents too (PDFs, notes, Word files and the rest). PDFs, notes and Word files get a Quick Look thumbnail, and a folder that holds a `.git` folder is left out and named, because a copy of code is checked as a whole, not sorted file by file.

### On the page

| Key | What it does |
|---|---|
| Click, Shift-click | Select, select a range |
| "select folder" | Select all of a folder |
| "+ subfolders" | Select a folder and everything below it |
| ⌘A (Ctrl-A) | Select everything shown: type a word in the filter first, then ⌘A |
| 1–9, 0 | Put the selection in that bucket |
| X | Take the selection out of its bucket |
| N | Name the selection (becomes a subfolder when moving) |
| Space, double-click | Full preview (PDFs and text files too); arrows move, Esc closes |
| "+ bucket" | Add a bucket |

It saves as you go. Close the page, stop the server, come back tomorrow: your choices are still there.

### In plan.json

```json
{
  "use_names_as_subfolders": true,
  "buckets": {
    "Work": "~/Sorted/Work",
    "Not sure": "",
    "Delete?": "TRASH"
  }
}
```

A folder path means "move there". `""` means "leave them where they are". `"TRASH"` puts them in the Trash, where Finder's "Put Back" still works. The first plan suggests `~/Sorted/<bucket>` for every bucket and never suggests the Trash: you write `TRASH` yourself.

## Safe by design

- `make_sheet.py` and the page only read your files. Only `apply.py --go` moves anything.
- It never overwrites a file. A name that is taken gets " (2)".
- It never deletes. The Trash is as far as it goes, and only for buckets you mark.
- The page listens on 127.0.0.1, so no other computer can reach it, and it only serves files that are in your sheet.
- Your thumbnails and file list stay in `data/`, which is ignored by git.

## Good to know

- **iCloud:** files that live only in iCloud ("Optimize Mac Storage") show "only in iCloud" instead of a thumbnail, because making one would download them. To see them, Control-click the folder in Finder and choose **Keep Downloaded** (it downloads everything inside, so check the folder's size and your free space first), then run `make_sheet.py` again. Moving files on the same disk is a rename, so files only in iCloud can be moved without downloading them. If your Desktop and Documents sync to iCloud, whatever you move or trash there changes on your other devices too. The `trash` command can refuse files in iCloud Drive; `apply.py --go` then says how many stayed where they are, and you drag those to the Trash in Finder.
- **Big folders:** making the sheet for 4,784 files took under two minutes on my Mac. Thumbnails are reused when you run it again.
- **Documents** come in with `--all`. A text or HTML file is shown as plain text, so nothing in it runs on the page. Zips, installers and Word files show their thumbnail only.

## License

MIT. See [LICENSE](LICENSE).
