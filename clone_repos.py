#!/usr/bin/env python3
"""Clone or update git repositories from a CSV file of repository_url,branch pairs."""

import argparse
import csv
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


def repo_dir_name(url, branch):
    name = url.rstrip("/").rsplit("/", 1)[-1]
    name = re.sub(r"\.git$", "", name)
    org = url.rstrip("/").rsplit("/", 2)[-2]
    org = re.sub(r"^.*[:/]", "", org)
    safe_branch = re.sub(r"[^\w.-]", "_", branch)
    return f"{org}_{name}_{safe_branch}"


def clone_or_update(repo_url, branch, base_dir):
    dest = os.path.join(base_dir, repo_dir_name(repo_url, branch))

    if os.path.isdir(dest):
        result = subprocess.run(
            ["git", "-C", dest, "fetch", "--depth", "1", "origin", branch],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return repo_url, False, f"fetch failed: {result.stderr.strip()}"
        result = subprocess.run(
            ["git", "-C", dest, "checkout", f"origin/{branch}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return repo_url, False, f"checkout failed: {result.stderr.strip()}"
        return repo_url, True, "updated"

    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", "--branch", branch, repo_url, dest],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return repo_url, False, f"clone failed: {result.stderr.strip()}"
    return repo_url, True, "cloned"


def read_repos(file_path, default_branch):
    repos = []
    with open(file_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or not row[0].strip():
                continue
            url = row[0].strip()
            branch = row[1].strip() if len(row) > 1 and row[1].strip() else default_branch
            repos.append((url, branch))
    return repos


def main():
    parser = argparse.ArgumentParser(description="Clone repos from a CSV file")
    parser.add_argument("file", help="Input file (repository_url,branch per line)")
    parser.add_argument("--dest", default="repos", help="Base directory for clones (default: repos)")
    parser.add_argument("--workers", type=int, default=16, help="Parallel workers (default: 16)")
    parser.add_argument("--default-branch", default="prod", help="Branch when not specified (default: prod)")
    args = parser.parse_args()

    repos = read_repos(args.file, args.default_branch)
    print(f"Processing {len(repos)} repositories with {args.workers} workers...", file=sys.stderr)

    success = 0
    failed = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(clone_or_update, url, branch, args.dest): url
            for url, branch in repos
        }
        for i, future in enumerate(as_completed(futures), 1):
            url, ok, msg = future.result()
            if ok:
                success += 1
            else:
                failed.append((url, msg))
            if i % 100 == 0 or i == len(repos):
                print(f"Progress: {i}/{len(repos)} ({success} ok, {len(failed)} failed)", file=sys.stderr)

    print(f"\nDone: {success} succeeded, {len(failed)} failed", file=sys.stderr)
    for url, msg in failed:
        print(f"  FAILED {url}: {msg}", file=sys.stderr)


if __name__ == "__main__":
    main()
