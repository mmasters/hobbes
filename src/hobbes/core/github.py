"""GitHub API client for fetching releases."""

import re
import httpx

from hobbes.models.release import Release


GITHUB_API_BASE = "https://api.github.com"


class GitHubError(Exception):
    """Error from GitHub API."""

    pass


def parse_repo_spec(spec: str) -> tuple[str, str]:
    """Parse a repo spec into (owner, repo).

    Accepts:
    - owner/repo
    - https://github.com/owner/repo
    - github.com/owner/repo
    """
    # Handle full URLs
    url_pattern = r"(?:https?://)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"
    match = re.match(url_pattern, spec)
    if match:
        return match.group(1), match.group(2)

    # Handle owner/repo format
    if "/" in spec:
        parts = spec.split("/")
        if len(parts) == 2:
            return parts[0], parts[1]

    raise ValueError(f"Invalid repo spec: {spec}. Use 'owner/repo' or GitHub URL.")


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self):
        self.client = httpx.Client(
            base_url=GITHUB_API_BASE,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def get_releases(
        self, owner: str, repo: str, per_page: int = 30
    ) -> list[Release]:
        """Get releases for a repository."""
        response = self.client.get(
            f"/repos/{owner}/{repo}/releases",
            params={"per_page": per_page},
        )

        if response.status_code == 404:
            raise GitHubError(f"Repository {owner}/{repo} not found")
        if response.status_code == 403:
            raise GitHubError("GitHub API rate limit exceeded")
        response.raise_for_status()

        releases = []
        for data in response.json():
            release = Release.from_api_response(data)
            if not release.draft:  # Skip draft releases
                releases.append(release)

        return releases

    def get_latest_release(self, owner: str, repo: str) -> Release:
        """Get the latest non-prerelease release."""
        response = self.client.get(f"/repos/{owner}/{repo}/releases/latest")

        if response.status_code == 404:
            # Fall back to getting all releases and finding first non-prerelease
            releases = self.get_releases(owner, repo)
            for release in releases:
                if not release.prerelease:
                    return release
            if releases:
                return releases[0]
            raise GitHubError(f"No releases found for {owner}/{repo}")

        response.raise_for_status()
        return Release.from_api_response(response.json())

    def get_release_by_tag(self, owner: str, repo: str, tag: str) -> Release:
        """Get a specific release by tag name."""
        response = self.client.get(f"/repos/{owner}/{repo}/releases/tags/{tag}")

        if response.status_code == 404:
            raise GitHubError(f"Release {tag} not found for {owner}/{repo}")
        response.raise_for_status()

        return Release.from_api_response(response.json())

    def search_repos(self, query: str, per_page: int = 10) -> list[dict]:
        """Search for repositories."""
        response = self.client.get(
            "/search/repositories",
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
            },
        )
        response.raise_for_status()

        items = response.json().get("items", [])
        return [
            {
                "full_name": item["full_name"],
                "description": item.get("description", ""),
                "stars": item["stargazers_count"],
                "url": item["html_url"],
            }
            for item in items
        ]
