"""Repos page: a fake git-status dashboard (mirrors the zelrepo idea)."""

from __future__ import annotations

import asyncio
import random

from textual.app import ComposeResult
from textual.widgets import DataTable, LoadingIndicator, Static

from .base import Page


class ReposPage(Page):
    TAB_ID = "repos"
    TAB_TITLE = "Repos"

    BINDINGS = [("r", "refresh_repos", "Refresh")]

    def compose(self) -> ComposeResult:
        yield Static("r refresh (simulates checking status)", classes="page-hint")
        yield DataTable(id="repos-table", cursor_type="row")
        yield LoadingIndicator(id="repos-loading")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Repo", "Branch", "Ahead", "Behind", "Dirty", "Last Commit")
        self.query_one("#repos-loading", LoadingIndicator).display = False

    def initial_focus_target(self):
        return self.query_one(DataTable)

    def commands(self) -> list[tuple[str, str, object]]:
        return [("Repos: Refresh", "Re-check fake repo status", self.action_refresh_repos)]

    def action_refresh_repos(self) -> None:
        self.run_worker(self._do_refresh(), exclusive=True)

    async def _do_refresh(self) -> None:
        loading = self.query_one("#repos-loading", LoadingIndicator)
        loading.display = True
        self.app.notify("checking repos...", timeout=2)

        await asyncio.sleep(0.8)

        for repo in self.store.repos:
            repo.ahead = random.randint(0, 6)
            repo.behind = random.randint(0, 2)
            repo.dirty = random.random() < 0.5
            repo.last_commit = random.choice(["just now", "5 minutes ago", "1 hour ago", "yesterday"])

        self.store.log("Refreshed repo statuses")
        loading.display = False
        self.refresh_from_store()
        self.app.notify("repo status refreshed", timeout=2)

    def refresh_from_store(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for repo in self.store.repos:
            table.add_row(repo.name, repo.branch, f"+{repo.ahead}", f"-{repo.behind}", "yes" if repo.dirty else "no", repo.last_commit)
