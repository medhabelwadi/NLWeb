# Use the GitHub API to extract data from a repository
import requests
import json
import os
import logging
from dotenv import load_dotenv

# ...existing code...

#This is what you need for the JSON-LD output:
#@type
#description
#name
#url

default_filename = "ghrepoinfo.json"


def get_all_pages(url, headers, params=None):
    results = []
    page = 1
    while True:
        logging.debug(f"Fetching page {page} for URL: {url} with params: {params}") 
        req_params = {} if not params else params.copy()
        req_params.update({"per_page": 100, "page": page})
        resp = requests.get(url, headers=headers, params=req_params)
        resp.raise_for_status()
        items = resp.json()
        if not items:
            logging.debug("No items returned, ending pagination")
            break
        results.extend(items)
        logging.debug(f"Page {page} returned {len(items)} items")
        page += 1
    return results

def main():
    load_dotenv()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Starting GitHub data extraction")

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        return

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    repos = get_all_pages("https://api.github.com/user/repos", headers)
    logging.info(f"Found {len(repos)} repositories")
    all_data = []
    remove_later = 0
    for repo in repos:
        owner = repo["owner"]["login"]
        #if owner != "jennifermarsman":
        #    continue
        name = repo["name"]
        logging.info(f"Processing repo {owner}/{name}")  # added
        print("Repo info: ", repo)
        #repo_json = json.loads(repo)
        repo["@type"] = "Repository"
        #repo["name"] = repo["name"]
        repo["description"] = repo.get("description", "")   # TODO: give a better default description
        repo["url"] = repo["html_url"]
        print("repo:---------------------------------------------------------------------------")
        print(repo)
        # Confirm that it always has a name and description?  
        # TODO: pull in some specific fields rather than everything so we don't hit embedding token limits
        
        issues_url = f"https://api.github.com/repos/{owner}/{name}/issues"
        issues = get_all_pages(issues_url, headers, {"state": "all"})
        logging.info(f"Fetched {len(issues)} issues for {owner}/{name}")
        if len(issues) > 0:
            print("example issue:", issues[0]) 
        for issue in issues:
            issue["@type"] = "Issue"
            issue["name"] = issue["title"]
            issue["description"] = issue.get("body", "")
            issue["url"] = issue["html_url"]
            # TODO: confirm that this is appending correctly
            print("issue:---------------------------------------------------------------------------")
            print(issue)
        repo["issues"] = issues
               
        pulls_url = f"https://api.github.com/repos/{owner}/{name}/pulls"
        pulls = get_all_pages(pulls_url, headers, {"state": "all"})
        logging.info(f"Fetched {len(pulls)} pull requests for {owner}/{name}")  # added
        if len(pulls) > 0:
            print("example pull request:", pulls[0])  # added
        for pull in pulls:
            pull["@type"] = "PullRequest"
            pull["name"] = pull["title"]
            pull["description"] = pull.get("body", "")
            pull["url"] = pull["html_url"]
        repo["pulls"] = pulls

        all_data.append({
            "repo": repo,
            #"issues": issues,
            #"pulls": pulls
        })


        # This is just for debugging, remove later
        with open("JenOneRepo.json", "w", encoding="utf-8") as f:
            json.dump(repo, f, indent=4)


        with open(default_filename, "a", encoding="utf-8") as f:
            json.dump(repo, f)
            f.write("\n")

        remove_later += 1
        if remove_later > 2:
            break

    logging.info(f"Wrote JSON-LD output to {default_filename}")  # added
    

    '''
    # Convert collected data into JSON-LD format
   #with open(default_filename, "w", encoding="utf-8") as f:
   #    json.dump(all_data, f, indent=2)
    jsonld = {
       "@context": {
           "schema": "https://schema.org/",
           "name": "schema:name",
           "description": "schema:description",
           "url": "schema:url",
           "issues": {"@id": "schema:hasPart", "@container": "@set"},
           "pullRequests": {"@id": "schema:hasPart", "@container": "@set"}
       },
       "@graph": []
    }
    for item in all_data:
       repo = item["repo"]
       issues = item["issues"]
       pulls = item["pulls"]
       graph_item = {
           "@type": "schema:SoftwareSourceCode",
           "schema:name": repo["name"],
           "schema:description": repo.get("description", ""),
           "schema:url": repo["html_url"],
           "issues": [
               {
                   "@type": "schema:DiscussionForumPosting",
                   "schema:name": i["title"],
                   "schema:description": i.get("body", ""),
                   "schema:url": i["html_url"]
               } for i in issues
           ],
           "pullRequests": [
               {
                   "@type": "schema:SoftwareSourceCode",
                   "schema:name": p["title"],
                   "schema:description": p.get("body", ""),
                   "schema:url": p["html_url"]
               } for p in pulls
           ]
       }
       jsonld["@graph"].append(graph_item)
    '''

    #logging.info(f"Writing JSON-LD output to {default_filename}")  # added
    #with open(default_filename, "w", encoding="utf-8") as f:
    #   json.dump(all_data, f)

if __name__ == "__main__":
    main()
