#!/usr/bin/env python3
"""Move sorted files into folders, with a log that undoes it.

  python3 apply.py <sheet>                 plan only: writes data/<sheet>/plan.json, moves nothing
  python3 apply.py <sheet> --go            moves the files as plan.json says and logs every move
  python3 apply.py <sheet> --undo <log>    moves the files of that log back

plan.json says where each bucket goes:
  "Work": "~/Sorted/Work"      move there (a file's name or topic becomes a subfolder)
  "Not sure": ""               leave those files where they are
  "Delete?": "TRASH"           put them in the Trash (Finder's "Put Back" undoes it)
The first run suggests ~/Sorted/<bucket> for every bucket and never TRASH: you write TRASH yourself.
A file is never overwritten: a name that is taken gets " (2)". Unsorted files stay where they are.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))


def safe(name):
    """A bucket or topic as one folder name: no slashes or colons."""
    return re.sub(r"[/:\\]+", "-", str(name)).strip(" .") or "unnamed"


def fmt(b):
    return f"{b / 1e9:.1f} GB" if b > 1e9 else f"{b / 1e6:.1f} MB" if b > 1e6 else f"{b / 1e3:.0f} KB"


def files(n):
    return f"{n} file" if n == 1 else f"{n} files"


def write_json(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def load(sheet):
    d = os.path.join(HERE, "data", sheet)
    if not os.path.exists(os.path.join(d, "items.json")):
        sys.exit(f"No sheet named {sheet}: run make_sheet.py first.")
    sheet_data = json.load(open(os.path.join(d, "items.json"), encoding="utf-8"))
    cp = os.path.join(d, "choices.json")
    choices = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    return d, sheet_data, choices


def plan(sheet):
    d, sheet_data, choices = load(sheet)
    used = [c.get("b") for k, c in choices.items() if k != "_buckets" and c.get("b")]
    buckets = list(dict.fromkeys(choices.get("_buckets", []) + used))
    pp = os.path.join(d, "plan.json")
    old = json.load(open(pp, encoding="utf-8")) if os.path.exists(pp) else {}
    targets = old.get("buckets", {})
    for b in buckets:
        targets.setdefault(b, f"~/Sorted/{safe(b)}")
    write_json(pp, {"use_names_as_subfolders": old.get("use_names_as_subfolders", True), "buckets": targets})

    count, size, gone = {}, {}, {}
    for it in sheet_data["items"]:
        b = (choices.get(it["id"]) or {}).get("b")
        if not b:
            continue
        count[b] = count.get(b, 0) + 1
        size[b] = size.get(b, 0) + it["size"]
        if not os.path.lexists(it["path"]):
            gone[b] = gone.get(b, 0) + 1
    unsorted = len(sheet_data["items"]) - sum(count.values())
    print(f"Plan for {sheet} (nothing moved). Edit {pp} to change a target.\n")
    for b in buckets:
        if not count.get(b):
            continue
        t = targets[b] or "(stays where it is)"
        extra = f", {gone[b]} no longer there" if gone.get(b) else ""
        print(f"  {b}: {files(count[b])}, {fmt(size[b])} -> {t}{extra}")
    print(f"\n  Unsorted: {files(unsorted)} stay where they are.")
    print(f"\nWhen the plan is right: python3 apply.py {sheet} --go")


def unique(path):
    if not os.path.lexists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.lexists(f"{stem} ({n}){ext}"):
        n += 1
    return f"{stem} ({n}){ext}"


def go(sheet):
    d, sheet_data, choices = load(sheet)
    pp = os.path.join(d, "plan.json")
    if not os.path.exists(pp):
        sys.exit(f"No plan yet: run  python3 apply.py {sheet}  first and read it.")
    p = json.load(open(pp, encoding="utf-8"))
    targets, subfolders = p.get("buckets", {}), p.get("use_names_as_subfolders", True)
    trash = shutil.which("trash")
    log = os.path.join(d, time.strftime("moves-%Y%m%d-%H%M%S.tsv"))
    moved = trashed = missing = skipped = 0
    with open(log, "w", encoding="utf-8") as fh:
        for it in sheet_data["items"]:
            c = choices.get(it["id"]) or {}
            t = targets.get(c.get("b") or "", "")
            if not c.get("b") or not t:
                continue
            src = it["path"]
            if not os.path.lexists(src):
                missing += 1
                continue
            if t == "TRASH":
                if not trash:
                    skipped += 1
                    continue
                if subprocess.run([trash, src], capture_output=True).returncode == 0:
                    fh.write(f"trash\t{src}\t\n"); fh.flush()
                    trashed += 1
                continue
            folder = os.path.expanduser(t)
            if subfolders and c.get("n", "").strip():
                folder = os.path.join(folder, safe(c["n"].strip()))
            if os.path.dirname(src) == folder:
                continue
            os.makedirs(folder, exist_ok=True)
            dst = unique(os.path.join(folder, os.path.basename(src)))
            shutil.move(src, dst)
            fh.write(f"move\t{src}\t{dst}\n"); fh.flush()
            it["path"] = dst
            moved += 1
    write_json(os.path.join(d, "items.json"), sheet_data)  # the sheet follows the files
    print(f"Moved {moved}, to the Trash {trashed}, already gone {missing}.")
    if not moved and not trashed:
        os.remove(log)  # the empty log this run just opened
        return
    if skipped:
        print(f"{skipped} files marked TRASH were left: this Mac has no `trash` command.")
    print(f"Log: {log}\nUndo: python3 apply.py {sheet} --undo {os.path.basename(log)}")
    print("If the sort page is open, restart server.py so it sees the new places.")


def undo(sheet, name):
    d, sheet_data, _ = load(sheet)
    log = name if os.path.isabs(name) else os.path.join(d, name)
    rows = [l.rstrip("\n").split("\t") for l in open(log, encoding="utf-8") if l.strip()]
    by_path = {it["path"]: it for it in sheet_data["items"]}
    back = left = trashed = 0
    for action, src, dst in reversed(rows):
        if action == "trash":
            trashed += 1
            continue
        if not os.path.lexists(dst) or os.path.lexists(src):
            left += 1
            continue
        os.makedirs(os.path.dirname(src), exist_ok=True)
        shutil.move(dst, src)
        if dst in by_path:
            by_path[dst]["path"] = src
        back += 1
    write_json(os.path.join(d, "items.json"), sheet_data)
    print(f"Moved back {back}. Left alone {left} (moved again since, or the old place is taken).")
    if trashed:
        print(f"{files(trashed)} went to the Trash: select them there and use Finder's Put Back.")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if len(a) == 1:
        plan(a[0])
    elif a[1] == "--go":
        go(a[0])
    elif a[1] == "--undo" and len(a) == 3:
        undo(a[0], a[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
