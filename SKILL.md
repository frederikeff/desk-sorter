---
name: desk-sorter
description: Tidy the images and videos in messy Mac folders (Downloads, Desktop, screenshots, old exports) by sight. Builds a local page that shows every picture and video as one long list of thumbnails; the person sorts them into their own buckets with number keys; then Claude proposes where each bucket goes and moves files only after the person's yes, with a log that undoes it. Use when someone wants to clean up, sort, organize or declutter pictures, screenshots or videos on their Mac.
---

# Desk Sorter

The person decides; you do the work around it. They look at their pictures and sort them on a page. You make the page, read what they chose, and move files only when they say yes.

Everything runs on their Mac. Pictures, thumbnails and file names never go to an outside service. Do not open or describe their pictures unless they ask: these are private files.

The scripts are in this skill's folder, the folder this file is in. Run them from there. They need macOS (they use `sips` and `qlmanage`) and `python3`; if `python3` is missing, macOS offers to install the Command Line Tools.

## 1. Which folders, and how big

Ask which folders to sort (Downloads and Desktop are the usual ones). Measure before anything else and tell them:

```
du -sh ~/Downloads
find ~/Downloads -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.heic' -o -iname '*.mov' -o -iname '*.mp4' \) | wc -l
```

Ask for their buckets: brands, projects, clients, "Personal", "Delete?", "Not sure". Their own words work best. They can add more on the page later.

## 2. Make the sheet (reads only)

```
python3 make_sheet.py <sheet> <folder> [<folder> ...] [--skip <folder>] --buckets "A,B,Delete?,Not sure"
```

`<sheet>` is a short name such as `downloads`. This writes `data/<sheet>/` (the list and 320 px thumbnails) and moves nothing. Report what it prints: images, videos, and how many live only in iCloud. Those get no thumbnail, because making one would download them. To see them, she Control-clicks the folder in Finder and chooses Keep Downloaded (it downloads everything inside: give the folder's size and the free disk space first), then you run `make_sheet.py` again. If Desktop and Documents sync to iCloud, a later delete there syncs to every device too: say so.

## 3. Open the page

Pick a free port (check that `lsof -ti tcp:8791` prints nothing), then start the server in the background:

```
python3 server.py <sheet> 8791
```

Give them http://127.0.0.1:8791 and the keys: click to select, Shift-click for a range, "select folder" for a whole folder, 1–9 and 0 to put the selection in a bucket, X to clear, N to give the selection a name or topic (it becomes a subfolder later), Space for a full preview. It saves by itself, so they can stop and come back.

Then wait. They may sort for hours. Don't ask whether they are done.

## 4. Propose the moves (still reads only)

When they say they are done, or want to move what they have so far:

```
python3 apply.py <sheet>
```

This writes `data/<sheet>/plan.json` and prints, for each bucket, how many files, how big, and where they would go (first suggestion: `~/Sorted/<bucket>`). Show them that list in plain words and ask where each bucket should go. Edit `plan.json` to match their answers:

- a folder path: move there;
- `""`: leave those files where they are;
- `"TRASH"`: to the Trash. Write this only for a bucket they have named for the Trash in this conversation.

## 5. Move, only at their yes

Show the final plan once more. Only after a clear yes:

```
python3 apply.py <sheet> --go
```

It never overwrites (a taken name gets " (2)"), logs every move in `data/<sheet>/moves-<time>.tsv`, and prints the undo command. Tell them the counts and where the log is. Never use `rm`. Never empty the Trash.

To undo: `python3 apply.py <sheet> --undo <log file>`. Files sent to the Trash come back with Finder's "Put Back".

## 6. Close

Stop the server by its port: `lsof -ti tcp:8791 | xargs kill`. The `data/` folder holds their thumbnails and file paths. It stays on their Mac and should never go into git. They may delete it when they no longer need the sheet.
