#!/usr/bin/env python3
"""Fetch all projects from an AAP 2.6 Controller API with pagination."""

import argparse
import getpass
import urllib3

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def build_session(token=None, username=None, password=None):
    session = requests.Session()
    session.headers["Content-Type"] = "application/json"
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    elif username and password:
        session.auth = (username, password)
    return session


def get_all_projects(base_url, session, verify_ssl=True, page_size=50):
    url = f"{base_url}/api/controller/v2/projects/?page_size={page_size}"
    projects = []

    while url:
        resp = session.get(url, verify=verify_ssl)
        resp.raise_for_status()
        data = resp.json()
        projects.extend(data["results"])
        # print(f"Fetched {len(projects)}/{data['count']} projects...")
        next_url = data.get("next")
        if next_url:
            url = base_url + next_url
        else:
            url = None

    return projects


def main():
    parser = argparse.ArgumentParser(description="Fetch all AAP 2.6 projects")
    parser.add_argument("--url", required=True, help="Controller base URL (e.g. https://aap.example.com)")
    auth_group = parser.add_mutually_exclusive_group(required=True)
    auth_group.add_argument("--token", help="OAuth2 bearer token")
    auth_group.add_argument("--username", "-u", help="Username (will prompt for password)")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification")
    parser.add_argument("--page-size", type=int, default=50, help="Results per page (default: 50)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    password = getpass.getpass("Password: ") if args.username else None
    session = build_session(token=args.token, username=args.username, password=password)
    projects = get_all_projects(base_url, session, verify_ssl=not args.no_verify_ssl, page_size=args.page_size)

    for p in projects:
        if p.get("scm_url"):
            print(f"{p['scm_url']},{p['scm_branch']}")


if __name__ == "__main__":
    main()
