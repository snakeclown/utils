import os
import requests
from github import Github

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "<missing-github-token>")

QUERY = "topic:owned-by-services org:slicelife"

API_URL = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

def run_graphql(query, variables=None):
    response = requests.post(API_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f"GraphQL query failed: {response.status_code} {response.text}")
    data = response.json()
    if "errors" in data:
        raise Exception(f"GraphQL error: {data['errors']}")
    return data["data"]

# GraphQL query to search repos and get latest production deployment
graphql_query = """
query($searchQuery: String!, $after: String) {
  search(query: $searchQuery, type: REPOSITORY, first: 50, after: $after) {
    repositoryCount
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on Repository {
        nameWithOwner
        description
        updatedAt
        deployments(environments: ["production"], first: 1, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            createdAt
          }
        }
      }
    }
  }
}
"""

def get_repo_info(search_query):
    after = None
    while True:
        variables = {"searchQuery": search_query, "after": after}
        data = run_graphql(graphql_query, variables)
        search_data = data["search"]

        for repo in search_data["nodes"]:
            name = repo["nameWithOwner"]
            description = repo["description"] or "(no description)"
            updated_at = repo["updatedAt"]
            deployments = repo["deployments"]["nodes"]
            prod_deploy = deployments[0]["createdAt"] if deployments else None

            # Not in graphql repo data
            details = get_repo_details(name)

            yield name, description, updated_at, prod_deploy, details

        if not search_data["pageInfo"]["hasNextPage"]:
            break
        after = search_data["pageInfo"]["endCursor"]


def get_repo_details(repo_name, token=GITHUB_TOKEN):
    g = Github(token) if token else Github()

    repo = g.get_repo(repo_name)
    languages = repo.get_languages()
    if languages:
        main_language = max(languages, key=languages.get)
    else:
        main_language = "No languages detected"

    # Get open Dependabot PRs count
    open_prs = repo.get_pulls(state="open")
    open_dependabot_count = 0

    for pr in open_prs:
        # Check multiple conditions for Dependabot PRs
        if (pr.user.login in ['dependabot[bot]', 'dependabot-preview[bot]'] or
                'dependabot' in pr.title.lower() or
                'dependabot' in pr.head.ref):
            open_dependabot_count += 1

    last_feat = "No feature PR found"
    for pr in repo.get_pulls(state="closed"):
        # Check if PR starts with "feat" AND was actually merged (not just closed)
        if (pr.title and
                pr.title.lower().startswith("feat") and
                pr.merged_at is not None):
            last_feat = pr.merged_at
            break

    return f"{main_language};{open_dependabot_count};{last_feat}"

if __name__ == "__main__":
    for name, description, updated_at, prod_deploy, details in get_repo_info(QUERY):
        if not prod_deploy:
            prod_deploy = "(none found)"
        print(f"{name};{description};{details};{updated_at};{prod_deploy}")
