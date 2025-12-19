"""Search command implementation."""

import click
from rich.console import Console
from rich.table import Table

from hobbes.core.github import GitHubClient, GitHubError

console = Console()


@click.command()
@click.argument("query")
@click.option("--limit", "-n", default=10, help="Number of results to show")
def search(query: str, limit: int):
    """Search GitHub for packages.

    QUERY is the search term (e.g., 'fuzzy finder', 'json parser').
    """
    console.print(f"[blue]Searching for:[/blue] {query}\n")

    with GitHubClient() as client:
        try:
            results = client.search_repos(query, per_page=limit)
        except GitHubError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

    if not results:
        console.print("No results found")
        raise SystemExit(0)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Repository")
    table.add_column("Stars")
    table.add_column("Description")

    for repo in results:
        desc = repo["description"] or ""
        if len(desc) > 60:
            desc = desc[:57] + "..."
        table.add_row(
            repo["full_name"],
            f"⭐ {repo['stars']:,}",
            desc,
        )

    console.print(table)
    console.print("\n[dim]Install with: hobbes install <owner/repo>[/dim]")
