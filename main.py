# python main.py

ORG = "dask"
REPO = "dask"


def pull_issues(org: str = ORG, repo: str = REPO) -> None:
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
        # Open issues and PRs
        issues_url = f"https://api.github.com/repos/{org}/{repo}/issues?state=open&per_page=100&page={page}"
        response = requests.get(issues_url, headers=headers)
        if response.status_code != 200:
            break
        page_issues = response.json()
        if not page_issues:
            break
        only_issues = [issue for issue in page_issues if "pull_request" not in issue]
        issues.extend(only_issues)
        page += 1

    for issue in tqdm(issues, "fetching issues"):
        issue_number = issue["number"]
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


def concat_issues(repo: str = REPO) -> None:
    import json
    import os
    import pandas as pd

    from tqdm.auto import tqdm

    df = pd.DataFrame()
    for file in tqdm(sorted(os.listdir(f"{repo}_issues")), "concatenating issues"):
        with open(f"{repo}_issues/{file}", "r") as f:
            data = json.load(f)
        _df = pd.json_normalize(data)
        _df["label_names"] = _df["labels"].apply(
            lambda x: [label["name"] for label in x] if isinstance(x, list) else []
        )
        # TODO remove issue template?
        df = pd.concat([df, _df], axis=0).reset_index(drop=True)

    df = df.rename(
        columns={
            "comments": "n_comments",
            "user.login": "issue_user.login",
            "body": "issue_text",
            "reactions.total_count": "issue_reactions.total_count",
            "reactions.+1": "issue_reactions.+1",
            "reactions.-1": "issue_reactions.-1",
            "reactions.laugh": "issue_reactions.laugh",
            "reactions.hooray": "issue_reactions.hooray",
            "reactions.confused": "issue_reactions.confused",
            "reactions.heart": "issue_reactions.heart",
            "reactions.rocket": "issue_reactions.rocket",
            "reactions.eyes": "issue_reactions.eyes",
            "created_at": "issue_created_at",
            "updated_at": "issue_updated_at",
        }
    )

    df.to_csv(f"{repo}_issue_details.csv")
    # Unique issue creators
    df.rename(
        columns={
            "issue_user.login": "user.login",
        }
    )["user.login"].drop_duplicates().reset_index(drop=True).to_csv(
        f"{repo}_issue_posters.csv"
    )

    return None


def pull_comments(repo: str = REPO) -> None:
    # Pull comments for issues already pulled
    import os
    import requests
    import pandas as pd
    import json

    from tqdm.auto import tqdm

    output_folder = f"{repo}_comments"
    os.makedirs(output_folder, exist_ok=True)

    df = pd.read_csv(f"{repo}_issue_details.csv")

    headers = {"Authorization": f"token {os.environ['GITHUB_API_TOKEN']}"}

    for url in tqdm(df["comments_url"], "fetching comments"):
        issue = url.split("/")[-2]
        padded_issue = f"{int(issue):05d}"
        comment_detail_response = requests.get(url, headers=headers)
        comment_detail = comment_detail_response.json()
        file_path = os.path.join(output_folder, f"issue_comment_{padded_issue}.json")
        with open(file_path, "w") as f:
            json.dump(comment_detail, f, indent=4)

    return None


def concat_comments(repo: str = REPO) -> None:
    # One row is one comment
    import json
    import os
    import pandas as pd

    from tqdm.auto import tqdm

    df = pd.DataFrame()
    for file in tqdm(sorted(os.listdir(f"{repo}_comments")), "concatenating comments"):
        with open(f"{repo}_comments/{file}", "r") as f:
            data = json.load(f)
        _df = pd.json_normalize(data)
        df = pd.concat([df, _df], axis=0).reset_index(drop=True)

    # Add number to join with issues
    df["number"] = (
        df["html_url"].str.split("/", expand=True)[6].str.split("#", expand=True)[0]
    ).astype(int)

    df = df.rename(
        columns={
            "comments": "n_comments",
            "user.login": "comment_user.login",
            "body": "comment_text",
            "reactions.total_count": "comment_reactions.total_count",
            "reactions.+1": "comment_reactions.+1",
            "reactions.-1": "comment_reactions.-1",
            "reactions.laugh": "comment_reactions.laugh",
            "reactions.hooray": "comment_reactions.hooray",
            "reactions.confused": "comment_reactions.confused",
            "reactions.heart": "comment_reactions.heart",
            "reactions.rocket": "comment_reactions.rocket",
            "reactions.eyes": "comment_reactions.eyes",
            "created_at": "comment_created_at",
            "updated_at": "comment_updated_at",
        }
    )

    df.to_csv(f"{repo}_comment_details.csv")
    # Unique commenters
    df.rename(
        columns={
            "comment_user.login": "user.login",
        }
    )["user.login"].drop_duplicates().reset_index(drop=True).to_csv(
        f"{repo}_comment_commenters.csv"
    )
    return None


def pull_users(repo: str = REPO) -> None:
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

    for username in tqdm(df["user.login"], "fetching data for users"):
        user_detail_response = requests.get(
            f"https://api.github.com/users/{username}",
            headers=headers,
        )
        user_detail = user_detail_response.json()
        file_path = os.path.join(output_folder, f"user_detail_{username}.json")
        with open(file_path, "w") as f:
            json.dump(user_detail, f, indent=4)
    return None


def concat_users(repo: str = REPO) -> None:
    import json
    import os
    import numpy as np
    import pandas as pd
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderUnavailable

    from tqdm.auto import tqdm

    geolocator = Nominatim(user_agent="_", timeout=10)

    df = pd.DataFrame()
    for file in tqdm(sorted(os.listdir(f"{repo}_users")), "concatenating users"):
        with open(f"{repo}_users/{file}", "r") as f:
            data = json.load(f)
        _df = pd.json_normalize(data)
        _df["name_company"] = f"{_df['name'].values[0]} ({_df['company'].values[0]})"
        try:
            geocoded_location = geolocator.geocode(_df["location"].values)
            _df["location_lat"] = geocoded_location.latitude
            _df["location_lon"] = geocoded_location.longitude
        except GeocoderUnavailable:
            pass
        except AttributeError:
            _df["location_lat"] = np.nan
            _df["location_lon"] = np.nan

        df = pd.concat([df, _df], axis=0).reset_index(drop=True)
    df = df.rename(columns={"login": "user.login"})
    df.to_csv(f"{repo}_user_details.csv")
    return None


def create_table(repo: str = REPO) -> None:
    # Create a single dataframe

    # Filter out bots
    BOTS = ["dependabot[bot]", "GPUtester", "github-actions[bot]"]

    import pandas as pd

    core_columns = [
        "number",
        "title",
        "issue_text",
        "issue_user.login",
        "author_association",
        "label_names",
        # "state",
        # "locked",
        # "milestone",
        "issue_created_at",
        "issue_updated_at",
        "issue_reactions.total_count",
        "issue_reactions.+1",
        "issue_reactions.-1",
        "issue_reactions.laugh",
        "issue_reactions.hooray",
        "issue_reactions.confused",
        "issue_reactions.heart",
        "issue_reactions.rocket",
        "issue_reactions.eyes",
        "n_comments",
    ]
    df_issues = pd.read_csv(f"{repo}_issue_details.csv")[core_columns]
    df_issues = df_issues.loc[~df_issues["issue_user.login"].isin(BOTS)].reset_index(
        drop=True
    )

    core_columns = [
        "number",
        "comment_text",
        "comment_user.login",
        "comment_created_at",
        "comment_updated_at",
        "comment_reactions.total_count",
        "comment_reactions.+1",
        "comment_reactions.-1",
        "comment_reactions.laugh",
        "comment_reactions.hooray",
        "comment_reactions.confused",
        "comment_reactions.heart",
        "comment_reactions.rocket",
        "comment_reactions.eyes",
    ]
    df_comments = pd.read_csv(f"{repo}_comment_details.csv")[core_columns]
    df_comments = df_comments.loc[
        ~df_comments["comment_user.login"].isin(BOTS)
    ].reset_index(drop=True)

    core_columns = [
        "user.login",
        "name",
        "email",
        "company",
        "name_company",
        "location",
        "location_lat",
        "location_lon",
        "followers",
    ]
    df_users = pd.read_csv(f"{repo}_user_details.csv")[core_columns]
    df_users = df_users.loc[~df_users["user.login"].isin(BOTS)].reset_index(drop=True)

    df = df_comments.merge(df_issues)
    df = df.merge(df_users, left_on="issue_user.login", right_on="user.login").rename(
        columns={
            "email": "issue_user.login_email",
            "name": "issue_user.login_name",
            "company": "issue_user.login_company",
            "name_company": "issue_user.login_name_company",
            "location": "issue_user.login_location",
            "location_lat": "issue_user.login_location_lat",
            "location_lon": "issue_user.login_location_lon",
            "followers": "issue_user.login_followers",
        }
    )
    df = df.merge(df_users, left_on="comment_user.login", right_on="user.login").rename(
        columns={
            "email": "comment_user.login_email",
            "name": "comment_user.login_name",
            "company": "comment_user.login_company",
            "name_company": "comment_user.login_name_company",
            "location": "comment_user.login_location",
            "location_lat": "comment_user.login_location_lat",
            "location_lon": "comment_user.login_location_lon",
            "followers": "comment_user.login_followers",
        }
    )
    order_cols = [
        "number",
        "title",
        "issue_text",
        "label_names",
        "issue_user.login",
        "author_association",
        "issue_user.login_name",
        "issue_user.login_company",
        "issue_user.login_name_company",
        "issue_user.login_email",
        "issue_user.login_followers",
        "issue_user.login_location",
        "issue_user.login_location_lat",
        "issue_user.login_location_lon",
        "issue_created_at",
        "issue_updated_at",
        "issue_reactions.total_count",
        "issue_reactions.+1",
        "issue_reactions.-1",
        "issue_reactions.laugh",
        "issue_reactions.hooray",
        "issue_reactions.confused",
        "issue_reactions.heart",
        "issue_reactions.rocket",
        "issue_reactions.eyes",
        "n_comments",
        "comment_text",
        "comment_user.login",
        "comment_user.login_name",
        "comment_user.login_company",
        "comment_user.login_name_company",
        "comment_user.login_email",
        "comment_user.login_followers",
        "comment_user.login_location",
        "comment_user.login_location_lat",
        "comment_user.login_location_lon",
        "comment_created_at",
        "comment_updated_at",
        "comment_reactions.total_count",
        "comment_reactions.+1",
        "comment_reactions.-1",
        "comment_reactions.laugh",
        "comment_reactions.hooray",
        "comment_reactions.confused",
        "comment_reactions.heart",
        "comment_reactions.rocket",
        "comment_reactions.eyes",
    ]
    df = df[order_cols]

    df.to_parquet(f"{repo}_issue_with_comments.parquet")
    # Small version with just issue and some stats from comments
    commenters = df.groupby("number")["comment_user.login_name_company"].agg(list)
    comment_reactions = df.groupby("number")["comment_reactions.total_count"].sum()

    # df_issue_stats = df.groupby("number")[
    #     [
    #         "n_comments",
    #         "issue_reactions.total_count",
    #         "issue_reactions.+1",
    #         "issue_reactions.-1",
    #         "issue_reactions.laugh",
    #         "issue_reactions.hooray",
    #         "issue_reactions.confused",
    #         "issue_reactions.heart",
    #         "issue_reactions.rocket",
    #         "issue_reactions.eyes",
    #     ]

    # df.group
    # # Get unique posters
    # df["author.login"].drop_duplicates().to_csv(f"{repo}_issue_posters.csv")
    # # Get unique commenters
    # df["commenters"].explode().drop_duplicates().dropna().reset_index(drop=True).to_csv(
    #     f"{repo}_issue_commenters.csv"
    # )


if __name__ == "__main__":
    # pythohn main.py

    # pull_issues()
    # concat_issues()
    # pull_comments()
    # concat_comments()
    # pull_users()
    # concat_users()
    create_table()
