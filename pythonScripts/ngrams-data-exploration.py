import pandas as pd
import BeautifulSoup as bs
import os
import graphlab as gl
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from scipy import io
import numpy as np
import math
from numpy import inf
import pickle
from os.path import dirname
from sklearn.preprocessing import normalize
from nltk.stem.snowball import SnowballStemmer
import string
import nltk
from nltk.corpus import stopwords

pd.options.display.max_rows = 100
pd.options.display.max_columns = 100


# # Create Data folder for further usage


#get_ipython().magic(u"run 'text-mapping-circuit-filesystem.ipynb'")


# # Generate tf-idf circuit court data
stemmer = SnowballStemmer("english")
data = gl.SFrame({'filename':[""], 'text':[""]})
count = 0
for root, dirs, files in os.walk('../data/circuit-scbd-mapped-files/', topdown=False):
    for idx,name in enumerate(files):
        if ".p" in name:
            res = pickle.load(open( os.path.join(root, name), "rb" ))
            res = " ".join(res)
            res = " ".join([stemmer.stem(word) for word in res.split(" ")])
            res = "".join(l for l in res if l not in string.punctuation)
            res = res.encode('ascii', 'ignore').decode('ascii')

            words = nltk.word_tokenize(res)
            filtered_words = [word for word in words if word not in stopwords.words('english')]
            my_bigrams = list(nltk.bigrams(filtered_words))
            my_trigrams = list(nltk.trigrams(filtered_words))
            print my_bigrams
            df = gl.SFrame({'filename':[name], 'text':[str(res)], 'bigram':my_bigrams,'trigram':my_trigrams})
            data = data.append(df)
        print str(count) + str(" Done!!")
        count = count + 1

bigram_count = gl.text_analytics.count_words(data['bigram'])
trigram_count = gl.text_analytics.count_words(data['trigram'])

data['tf_idf_bi'] = gl.text_analytics.tf_idf(bigram_count)
data['tf_idf_tri'] = gl.text_analytics.tf_idf(trigram_count)




# This is added since the first data element is empty.
data = data[1:]
data = data.add_row_number()
data.save('../data/tf-idf-dataframe')


## load output
data = gl.load_sframe('../data/tf-idf-dataframe')


def dataframe_to_scipy_sparse(x, column_name):
    '''
    Convert a dictionary column of an SFrame into a sparse matrix format where
    each (row_id, column_id, value) triple corresponds to the value of
    x[row_id][column_id], where column_id is a key in the dictionary.

    Example
    >>> sparse_matrix, map_key_to_index = sframe_to_scipy(sframe, column_name)
    '''
    assert x[column_name].dtype() == dict,         'The chosen column must be dict type, representing sparse data.'

    # Create triples of (row_id, feature_id, count).
    # 1. Stack will transform x to have a row for each unique (row, key) pair.
    x = x.stack(column_name, ['feature', 'value'])

    # Map words into integers using a OneHotEncoder feature transformation.
    f = gl.feature_engineering.OneHotEncoder(features=['feature'])
    # 1. Fit the transformer using the above data.
    f.fit(x)
    # 2. The transform takes 'feature' column and adds a new column 'feature_encoding'.
    x = f.transform(x)
    # 3. Get the feature mapping.
    mapping = f['feature_encoding']
    # 4. Get the feature id to use for each key.
    x['feature_id'] = x['encoded_features'].dict_keys().apply(lambda x: x[0])

    # Create numpy arrays that contain the data for the sparse matrix.
    i = np.array(x['id'])
    j = np.array(x['feature_id'])
    v = np.array(x['value'])

    width = x['id'].max() + 1
    height = x['feature_id'].max() + 1
    # Create a sparse matrix.
    mat = csr_matrix((v, (i, j)), shape=(width, height))

    return mat, mapping



tf_idf, map_index_to_word = dataframe_to_scipy_sparse(data, 'tf_idf')
tf_idf_normalise = normalize(tf_idf)


# ### Save sparse matrix representation
io.mmwrite("../data/tf-idf-sparse.mtx", tf_idf)
io.mmwrite("../data/tf-idf-sparse-normalized.mtx", tf_idf_normalise)


# back to sparse matrix
#newm = io.mmread("data/tf-idf-sparse")
#newm_norm = io.mmread("data/tf-idf-sparse-normalized")
#tf_idf = newm.tocsr()
#tf_idf_normalise = newm_norm.tocsr()


# change sparse matrix to dense matrix.
#dense = tf_idf.todense()
