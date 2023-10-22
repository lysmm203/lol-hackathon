import tensorflow_recommenders as tfrs
import tensorflow_datasets as tfds

import os
import pprint
import tempfile

from typing import Dict, Text

import numpy as np
import tensorflow as tf
import tensorflow_datasets as tfds


# Ratings data.
ratings = tfds.load("movielens/100k-ratings", split="train")
# Features of all the available movies.
movies = tfds.load("movielens/100k-movies", split="train")


ratings = ratings.map(lambda x:{
    "user_id": x["user_id"],
    "movie_title": x["movie_title"]
})

movies = movies.map(lambda x: {
    "movie_title": x["movie_title"]
})

for movie in movies:
    print(movie)


# counter = 0
#
# movie_titles = movies.batch(1_000)
# user_ids = ratings.batch(1_000_000).map(lambda x: x["user_id"])
#
# unique_movie_titles = np.unique(np.concatenate(list(movie_titles)))
# unique_user_ids = np.unique(np.concatenate(list(user_ids)))
#
# print('A')


