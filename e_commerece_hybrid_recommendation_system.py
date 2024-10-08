# -*- coding: utf-8 -*-
"""E-Commerece Hybrid Recommendation System.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1nbyxsFD5ALY7ACPsLMgDtuHvu2WuUM1i

# Step 0: Load Packages and Libraries
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from scipy.sparse import coo_matrix



"""# Step 1: Data Loading and Preprocessing"""

# Read your dataset
train_data = pd.read_csv('/content/marketing_sample_for_walmart_com-walmart_com_product_review__20200701_20201231__5k_data.csv')

# Selecting relevant columns
train_data = train_data[['Uniq Id', 'Product Id', 'Product Rating', 'Product Reviews Count',
                         'Product Category', 'Product Brand', 'Product Name',
                         'Product Image Url', 'Product Description', 'Product Tags']]

# Renaming columns for easier handling
column_name_mapping = {
    'Uniq Id': 'ID',
    'Product Id': 'ProdID',
    'Product Rating': 'Rating',
    'Product Reviews Count': 'ReviewCount',
    'Product Category': 'Category',
    'Product Brand': 'Brand',
    'Product Name': 'Name',
    'Product Image Url': 'ImageURL',
    'Product Description': 'Description',
    'Product Tags': 'Tags'
}
train_data.rename(columns=column_name_mapping, inplace=True)

# Handling missing values
train_data.fillna({
    'Rating': 0,
    'ReviewCount': 0,
    'Category': '',
    'Brand': '',
    'Description': '',
    'Tags': ''
}, inplace=True)

# Extract numeric values from ID and ProdID columns
train_data['ID'] = train_data['ID'].str.extract(r'(\d+)').astype(float)
train_data['ProdID'] = train_data['ProdID'].str.extract(r'(\d+)').astype(float)

"""# Step 2: Exploratory Data Analysis (EDA)"""

# Basic statistics
num_users = train_data['ID'].nunique()
num_items = train_data['ProdID'].nunique()
num_ratings = train_data['Rating'].nunique()
print(f"Number of unique users: {num_users}")
print(f"Number of unique items: {num_items}")
print(f"Number of unique ratings: {num_ratings}")

# Distribution of interactions
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
train_data['ID'].value_counts().hist(bins=10, edgecolor='k')
plt.xlabel('Interactions per User')
plt.ylabel('Number of Users')
plt.title('Distribution of Interactions per User')

plt.subplot(1, 2, 2)
train_data['ProdID'].value_counts().hist(bins=10, edgecolor='k', color='green')
plt.xlabel('Interactions per Item')
plt.ylabel('Number of Items')
plt.title('Distribution of Interactions per Item')

plt.tight_layout()
plt.show()

"""# Step 3: Data Cleaning and Tags Creation"""

# Load the NLP model
nlp = spacy.load("en_core_web_sm")

# Function to clean and extract tags
def clean_and_extract_tags(text):
    doc = nlp(text.lower())
    tags = [token.text for token in doc if token.is_alpha and token.text not in STOP_WORDS]
    return ', '.join(tags)

# Extract tags from relevant columns and combine them
columns_to_extract_tags_from = ['Category', 'Brand', 'Description']
for column in columns_to_extract_tags_from:
    train_data[column] = train_data[column].apply(clean_and_extract_tags)

# Concatenate tags for further use in content-based recommendation
train_data['Tags'] = train_data[columns_to_extract_tags_from].apply(lambda row: ', '.join(row), axis=1)

"""# Step 4: Rating-Based Recommendation System"""

# Average ratings
average_ratings = train_data.groupby(['Name', 'ReviewCount', 'Brand', 'ImageURL'])['Rating'].mean().reset_index()
top_rated_items = average_ratings.sort_values(by='Rating', ascending=False)

# Display top 10 items
rating_base_recommendation = top_rated_items.head(10)
rating_base_recommendation[['Name', 'Rating', 'ReviewCount', 'Brand', 'ImageURL']]

"""# Step 5: Content-Based Recommendation System"""

# Function for content-based recommendations
def content_based_recommendations(train_data, item_name, top_n=10):
    # Check if the item exists
    if item_name not in train_data['Name'].values:
        print(f"Item '{item_name}' not found.")
        return pd.DataFrame()

    # Vectorize the tags and calculate similarities
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(train_data['Tags'])
    cosine_sim = cosine_similarity(tfidf_matrix)

    # Get the index and similarity scores
    item_index = train_data[train_data['Name'] == item_name].index[0]
    similarity_scores = list(enumerate(cosine_sim[item_index]))
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)

    # Get recommended items' indices
    top_indices = [i[0] for i in similarity_scores[1:top_n+1]]
    return train_data.iloc[top_indices][['Name', 'ReviewCount', 'Brand', 'ImageURL', 'Rating']]

# Example usage
item_name = 'OPI Infinite Shine, Nail Lacquer Nail Polish, Bubble Bath'
content_based_rec = content_based_recommendations(train_data, item_name, top_n=8)
content_based_rec

"""# Step 6: Collaborative Filtering Recommendation System"""

# Function for collaborative filtering recommendations
def collaborative_filtering_recommendations(train_data, target_user_id, top_n=10):
    user_item_matrix = train_data.pivot_table(index='ID', columns='ProdID', values='Rating', aggfunc='mean').fillna(0)
    user_similarity = cosine_similarity(user_item_matrix)
    target_user_index = user_item_matrix.index.get_loc(target_user_id)
    user_similarities = user_similarity[target_user_index]

    # Get similar users and items
    similar_user_indices = user_similarities.argsort()[::-1][1:]
    recommended_items = []

    for user_index in similar_user_indices:
        rated_by_similar_user = user_item_matrix.iloc[user_index]
        not_rated_by_target_user = (rated_by_similar_user > 0) & (user_item_matrix.iloc[target_user_index] == 0)
        recommended_items.extend(user_item_matrix.columns[not_rated_by_target_user][:top_n])

    # Get recommended item details
    recommended_items_details = train_data[train_data['ProdID'].isin(recommended_items)][['Name', 'ReviewCount', 'Brand', 'ImageURL', 'Rating']]
    return recommended_items_details.drop_duplicates().head(top_n)

# Example usage
target_user_id = 4
collaborative_filtering_rec = collaborative_filtering_recommendations(train_data, target_user_id, top_n=5)
collaborative_filtering_rec

"""# Step 7: Hybrid Recommendation System"""

# Function for hybrid recommendations
def hybrid_recommendations(train_data, target_user_id, item_name, top_n=10):
    content_based_rec = content_based_recommendations(train_data, item_name, top_n)
    collaborative_filtering_rec = collaborative_filtering_recommendations(train_data, target_user_id, top_n)
    hybrid_rec = pd.concat([content_based_rec, collaborative_filtering_rec]).drop_duplicates()
    return hybrid_rec.head(top_n)

# Example usage
item_name = 'OPI Nail Lacquer Polish .5oz/15mL - This Gown Needs A Crown NL U11'
hybrid_rec = hybrid_recommendations(train_data, target_user_id=4, item_name=item_name, top_n=10)
hybrid_rec