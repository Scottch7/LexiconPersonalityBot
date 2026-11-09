"""Upload the built site (deploy/build_site.py) to our free static Hugging Face Space.

Run by .github/workflows/deploy-questionnaire.yml on every merge to main that touches the app.
Needs the HF_TOKEN secret (a Hugging Face token with write access) in the GitHub repo settings.
"""
import os
import sys

from huggingface_hub import HfApi

SPACE = os.environ.get("HF_SPACE", "Scottch/lpb-questionnaire")


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "_site"
    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN is missing. Add it in GitHub: Settings > Secrets and variables > Actions.")
    api = HfApi(token=token)
    sha = os.environ.get("GITHUB_SHA", "local")[:7]
    # delete_patterns="*" removes files we no longer ship (Hugging Face keeps .gitattributes).
    commit = api.upload_folder(folder_path=folder, repo_id=SPACE, repo_type="space",
                               commit_message=f"Deploy questionnaire from GitHub {sha}", delete_patterns="*")
    print(f"Uploaded: {commit.commit_url}")
    print(f"Live at:  {api.space_info(SPACE).host}")


if __name__ == "__main__":
    main()
