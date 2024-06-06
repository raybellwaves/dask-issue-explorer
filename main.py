# python main.py


def pull_issues(org: str = "dask", repo: str = "dask") -> None:
    # Currently only open issues
    import os
    import requests
    import json

    from tqdm.auto import tqdm

    output_folder = f"{repo}_issues"
    os.makedirs(output_folder, exist_ok=True)

    headers = {"Authorization": f"token {os.environ['GITHUB_API_TOKEN']}"}

    issues = []
    page = 1
    while True:
        issues_url = f"https://api.github.com/repos/{org}/{repo}/issues?state=open&per_page=100&page={page}"
        response = requests.get(issues_url, headers=headers)
        if response.status_code != 200:
            break
        page_issues = response.json()
        if not page_issues:
            break
        issues.extend(page_issues)
        page += 1

    for issue in tqdm(issues):
        issue_number = issue["number"]
        print(f"Fetching issue details for issue {issue_number}")
        padded_issue_number = f"{issue_number:05d}"

        # Fetch issue details
        issue_detail_url = (
            f"https://api.github.com/repos/{org}/{repo}/issues/{issue_number}"
        )
        issue_detail_response = requests.get(issue_detail_url, headers=headers)
        issue_detail = issue_detail_response.json()

        # Save issue details to a file
        file_path = os.path.join(
            output_folder, f"issue_detail_{padded_issue_number}.json"
        )
        with open(file_path, "w") as f:
            json.dump(issue_detail, f, indent=4)

    return None


def concat_issues(repo: str = "dask") -> None:
    import json
    import os
    import pandas as pd

    from tqdm.auto import tqdm

    df = pd.DataFrame()
    for file in tqdm(sorted(os.listdir(f"{repo}_issues"))):
        with open(f"{repo}_issues/{file}", "r") as f:
            data = json.load(f)
        _df = pd.json_normalize(data)
        df = pd.concat([df, _df], axis=0).reset_index(drop=True)

    df = df.rename(columns={"comments": "n_comments"})

    df.to_csv(f"{repo}_issue_details.csv")
    # Unique issue posters
    df["user.login"].drop_duplicates().reset_index(drop=True).to_csv(
        f"{repo}_issue_posters.csv"
    )

    return None


def pull_comments(repo: str = "dask") -> None:
    # Pull comments for issues already pulled
    import os
    import requests
    import pandas as pd
    import json

    from tqdm.auto import tqdm

    output_folder = f"{repo}_comments"
    os.makedirs(output_folder, exist_ok=True)

    df = pd.read_csv("dask_issue_details.csv")

    headers = {"Authorization": f"token {os.environ['GITHUB_API_TOKEN']}"}

    for url in tqdm(df["comments_url"]):
        issue = url.split("/")[-2]
        padded_issue = f"{int(issue):05d}"
        comment_detail_response = requests.get(url, headers=headers)
        comment_detail = comment_detail_response.json()
        file_path = os.path.join(output_folder, f"issue_comment_{padded_issue}.json")
        with open(file_path, "w") as f:
            json.dump(comment_detail, f, indent=4)

    return None


def concat_comments(repo: str = "dask") -> None:
    # One row is one comment
    import json
    import os
    import pandas as pd

    from tqdm.auto import tqdm

    df = pd.DataFrame()
    for file in tqdm(sorted(os.listdir(f"{repo}_comments"))):
        with open(f"{repo}_comments/{file}", "r") as f:
            data = json.load(f)
        _df = pd.json_normalize(data)
        df = pd.concat([df, _df], axis=0).reset_index(drop=True)

    # Add number to join with issues
    df["number"] = (
        df["html_url"].str.split("/", expand=True)[6].str.split("#", expand=True)[0]
    ).astype(int)

    df.to_csv(f"{repo}_comment_details.csv")
    # Unique commenters
    df["user.login"].drop_duplicates().reset_index(drop=True).to_csv(
        f"{repo}_comment_commenters.csv"
    )

    return None


def pull_users(repo: str = "dask") -> None:
    import os
    import requests
    import pandas as pd
    import json

    from tqdm.auto import tqdm

    output_folder = f"{repo}_users"
    os.makedirs(output_folder, exist_ok=True)

    df_posters = pd.read_csv(f"{repo}_issue_posters.csv")
    df_commenters = pd.read_csv(f"{repo}_comment_commenters.csv")
    df = pd.concat([df_posters, df_commenters], axis=0)[
        ["user.login"]
    ].drop_duplicates()

    headers = {"Authorization": f"token {os.environ['GITHUB_API_TOKEN']}"}

    for username in tqdm(df["user.login"], "users"):
        user_detail_response = requests.get(
            f"https://api.github.com/users/{username}", headers=headers
        )
        user_detail = user_detail_response.json()
        file_path = os.path.join(output_folder, f"user_detail_{username}.json")
        with open(file_path, "w") as f:
            json.dump(user_detail, f, indent=4)

    return None


def concat_users(repo: str = "dask") -> None:
    import json
    import os
    import pandas as pd

    from tqdm.auto import tqdm

    df = pd.DataFrame()
    for file in tqdm(sorted(os.listdir(f"{repo}_users"))):
        with open(f"{repo}_users/{file}", "r") as f:
            data = json.load(f)
        _df = pd.json_normalize(data)
        df = pd.concat([df, _df], axis=0).reset_index(drop=True)

    df.to_csv(f"{repo}_user_details.csv")


def feature_engineering(repo: str = "dask") -> None:
    # Create a single dataframe
    import pandas as pd

    core_columns = [
        "number",
        "title",
        "body",
        "created_at",
        "updated_at",
        "closed_at",
        "author.login",
        "comments",
    ]
    df_issues = pd.read_csv("dask_issue_details.csv")[core_columns]

    def extract_label_names(labels):
        # Return labe names as lists
        # [], ["cudf.pandas","feature request"]
        raise NotImplementedError

    def flatten_comments(comments):
        # Flattens comments
        # [
        #     {"commenter": "raybelwaves", "comment": "comment 1", "reactions": {"thumbs_up": 2}},
        #     {"commenter": "someoneelse", "comment": "comment 2", "reactions": {"thumbs_up": 1}},
        # ]
        raise NotImplementedError

    def remove_issue_template(body):
        # Remove repeatable issue texts
        repeatable_texts = [
            "Thanks for opening an issue!",
            "please first ensure that there is no other issue present",
            "If there is no issue present please jump to a section below and delete the",
        ]
        for text in repeatable_texts:
            if text in body:
                return body.replace(text, "")

    df.to_csv(f"{repo}_issue_details.csv")
    # Get unique posters
    df["author.login"].drop_duplicates().to_csv(f"{repo}_issue_posters.csv")
    # Get unique commenters
    df["commenters"].explode().drop_duplicates().dropna().reset_index(drop=True).to_csv(
        f"{repo}_issue_commenters.csv"
    )


if __name__ == "__main__":
    # pull_issues()
    # concat_issues()
    # pull_comments()
    # concat_comments()
    # pull_users()
    # concat_users()
    feature_engineering()
