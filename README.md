# Data Processing Pipeline for Reddit Posts Analysis

The automation process starts with a Python web scraping script which obtains Reddit post information consisting of Title, Upvotes, Downvotes, Score, ID, URL, Comments, Created_UTC, Author, Flair and Shares. AWS EC2 Windows instance provides the execution environment that supports a scalable automated script operation.

After the data collection process the program saves the data as CSV format before moving it to an AWS S3 bucket for centralized storage and processing. AWS S3 serves as a flexible storage center that provides convenient database connectivity for additional AWS service integration.

The stored data gets transferred to Amazon Redshift through the COPY command that expedites large dataset movements from S3 to Redshift. The data structure process ensures that information becomes ready for relational analytics through an organized structure.

The loaded Redshift data becomes the basis for SQL query execution to generate data transformations and aggregation results and extract valuable insights. The database queries help with the evaluation of trends and the post rankings while allowing the measurement of engagement metrics and executing complicated analytical operations like window functions and conditional aggregations.

The ordered process creates a comprehensive system that automates data acquisition through storage and transformation operations which rely on AWS services to achieve scalable functionality.

### Flow Diagram
![*Flow Diagram*](Flow%20Diagram.jpg "Flow")


# Copied Data To Redshift

![*Data*](]Copied%20data.png "Data")

## Python Code
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

## Sql Queries 1
### Authors with Highly Viral Posts 
SELECT DISTINCT author 
FROM reddit_posts1 
WHERE score > (SELECT PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY score) FROM reddit_posts1);
![Q1](Authors%20with%20Highly%20Viral%20Posts.png "Q1")


## Sql Queries 2
### Largest % Increase in Engagement Day-to-Day

WITH EngagementData AS (
    SELECT created_utc, 
           SUM(upvotes + comments) AS daily_engagement
    FROM reddit_posts1
    GROUP BY created_utc
),
EngagementChange AS (
    SELECT created_utc, daily_engagement, 
           LAG(daily_engagement) OVER (ORDER BY created_utc) AS previous_day_engagement,
           ((daily_engagement - LAG(daily_engagement) OVER (ORDER BY created_utc)) / NULLIF(LAG(daily_engagement) OVER (ORDER BY created_utc), 0)) * 100 AS percentage_change
    FROM EngagementData
)
SELECT * FROM EngagementChange WHERE percentage_change IS NOT NULL ORDER BY percentage_change DESC LIMIT 5;

![*Q2*](Posts%20with%20the%20Largest%20%25%20Increase%20in%20Engagement%20Day-to-Day.png "Q2")


## Sql Queries 3
### Rank Posts by Upvotes Within Each Flair
SELECT title, flair, upvotes, 
       RANK() OVER (PARTITION BY flair ORDER BY upvotes DESC) AS rank_within_flair 
FROM reddit_posts1;

![*Q3*](Rank%20Posts%20by%20Upvotes%20Within%20Each%20Flair.png "Q3")

## Sql Queries 4
### Top 5 Most Upvoted Posts
SELECT title, upvotes, author, url 
FROM reddit_posts1 
ORDER BY upvotes DESC 
LIMIT 5;

![*Q4*](Top%205%20Most%20Upvoted%20Posts.png "Q4")

## Sql Queries 5
### Upvotes catagory wise
SELECT 
    SUM(CASE WHEN flair = 'Politics' THEN upvotes ELSE 0 END) AS Politics_Upvotes,
    SUM(CASE WHEN flair = 'Business' THEN upvotes ELSE 0 END) AS Business_Upvotes,
    SUM(CASE WHEN flair = 'Networking/Telecom' THEN upvotes ELSE 0 END) AS Networking_Upvotes
FROM reddit_posts1;
![*Q5*](Upvotes%20catagory%20wise.png "Q5")


# Guide to Running the Reddit Data Processing Pipeline

The first step to run this project requires users to launch the Remote Desktop Client (RDP) which enables access to the AWS EC2 Windows instance. Use the provided .pem key to obtain the necessary credentials when the RDP client demands a password. Users can obtain the administrator password by accessing the AWS EC2 Instances Connect section.

Locate the Python script dedicated for web scraping after establishing connection to the system. The provided Python file requires upload to the EC2 instance when the script file is not available. The already configured AWS CLI enables script execution to extract Reddit posts that save as CSV files within an S3 bucket.

The location (trybucket1010/reddit_data/technology_posts.csv) of the CSV file stored in S3 has been verified so you can execute this SQL command on Amazon Redshift to move the data into the reddit_posts1 table.

COPY reddit_posts1
FROM 's3://trybucket1010/reddit_data/technology_posts.csv'
IAM_ROLE 'arn:aws:iam::481665103654:role/redshiftroles'
FORMAT AS CSV
IGNOREHEADER 1;

Once the data is successfully copied, SQL queries can be executed on Amazon Redshift for further analysis and transformation. This setup ensures smooth automation of scraping, storage, and data processing.
