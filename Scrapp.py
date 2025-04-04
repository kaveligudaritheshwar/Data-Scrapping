import praw
import pandas as pd
import boto3
from datetime import datetime

# Initialize Reddit API
reddit = praw.Reddit(
    client_id="F0pUv6Djw4nQ792SDmT8eA",
    client_secret="L4jyu-fIENIuq5Trs21wTz52tx9Ymg",
    user_agent="Data_Scraper",
)

# AWS S3 Config
S3_BUCKET_NAME = "trybucket1010"  # Your S3 bucket
S3_OBJECT_NAME = "reddit_data/technology_posts.csv"  # Path inside S3

# Local CSV file path
local_csv_path = "C:\\temp\\technology_posts.csv"

subreddit_name = "technology"
post_limit_per_method = 1000  # Max posts per method
subreddit = reddit.subreddit(subreddit_name)
posts = []
seen_ids = set()

def calculate_votes(post):
    """Calculate Upvotes and Downvotes based on Score and Upvote Ratio."""
    upvotes = post.score
    upvote_ratio = post.upvote_ratio

    if upvote_ratio == 0.5:
        total_votes = upvotes * 2
    elif upvote_ratio == 1.0:
        total_votes = upvotes
    elif upvote_ratio == 0.0:
        total_votes = abs(upvotes)
    else:
        total_votes = upvotes / (2 * upvote_ratio - 1)

    downvotes = max(total_votes - upvotes, 0)
    return int(upvotes), int(downvotes)

def fetch_posts(source, method_name):
    """Fetch posts from different sorting methods and avoid duplicates."""
    count = 0
    for post in source:
        if post.id not in seen_ids:
            upvotes, downvotes = calculate_votes(post)
            posts.append([
                post.title, upvotes, downvotes, upvotes - downvotes,
                post.id, post.url, post.num_comments, datetime.utcfromtimestamp(post.created_utc).strftime('%Y-%m-%d'),
                post.author, post.link_flair_text, post.num_crossposts
            ])
            seen_ids.add(post.id)
            count += 1
        if count >= post_limit_per_method:
            break
    print(f"✅ Collected {count} posts from {method_name}")

# Collect Reddit posts
fetch_posts(subreddit.hot(limit=post_limit_per_method), "Hot Posts")
fetch_posts(subreddit.new(limit=post_limit_per_method), "New Posts")
for time_filter in ["all", "year", "month", "week"]:
    fetch_posts(subreddit.top(time_filter=time_filter, limit=post_limit_per_method), f"Top ({time_filter})")
fetch_posts(subreddit.search("technology", sort="new", limit=post_limit_per_method), "Search Results")

# Save CSV locally
df = pd.DataFrame(posts, columns=[
    "Title", "Upvotes", "Downvotes", "Score", "ID", "URL", "Comments",
    "Created_UTC", "Author", "Flair", "Shares"
])
df.to_csv(local_csv_path, index=False)
print(f"\n🚀 Data saved locally at: {local_csv_path}")

# Upload to S3
s3_client = boto3.client("s3")
try:
    s3_client.upload_file(local_csv_path, S3_BUCKET_NAME, S3_OBJECT_NAME)
    print(f"✅ CSV uploaded to S3: s3://{S3_BUCKET_NAME}/{S3_OBJECT_NAME}")
except Exception as e:
    print(f"❌ Failed to upload CSV to S3: {str(e)}")
