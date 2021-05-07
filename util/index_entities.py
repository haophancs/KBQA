#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on Jan 8, 2018

.. codeauthor: svitlana vakulenko
    <svitlana.vakulenko@gmail.com>

Index KG entities in ES

To restart indexing:

1. Delete previous index
curl -X DELETE "localhost:9200/dbpedia201604e"

2. Put mapping (see mapping.sh file)
curl -X PUT "localhost:9200/dbpedia201604e" -H 'Content-Type: application/json' -d'
...

3. Run this script. Check progress via
curl -XGET "localhost:9200/dbpedia201604e/_count"
DBpedia201604HDT contains 26,395,358 entities with the URIs starting http://dbpedia.org/

'''

from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk
from elasticsearch import TransportError

# setup
es = Elasticsearch()
doc_type = 'terms'  # for mapping

import re
import string

def parse_uri(entity_uri):
    entity_label = entity_uri.strip('/').split('/')[-1].strip('>')
    entity_label = " ".join(re.sub('([a-z])([A-Z])', r'\1 \2', entity_label).split())
    words = entity_label.split('_')
    unique_words = []
    for word in words:
        # strip punctuation
        word = "".join([c for c in word if c not in string.punctuation])
        if word:
            word = word.lower()
            if word not in unique_words:
                unique_words.append(word)
    entity_label = " ".join(unique_words)
    return entity_label


# define streaming function
def uris_stream(index_name, file_path, doc_type, ns_filter=None):
    with io.open(file_path, "r", encoding='utf-8') as infile:
        for i, line in enumerate(infile):
            # skip URIs if there is a filter set
            if ns_filter:
                if not line.startswith(ns_filter):
                    continue
            # line template http://creativecommons.org/ns#license;2
            parse = line.split(';')
            entity_uri = ';'.join(parse[:-1])

            entity_label = entity_uri.strip('/').split('/')[-1].strip('>').lower()
            label_words = parse_uri(entity_uri)
            count = parse[-1].strip()
            data_dict = {'uri': entity_uri, 'label': label_words,
                         'count': count, "id": i+1, 'label_exact': entity_label}

            yield {"_index": index_name,
                   "_type": doc_type,
                   "_source": data_dict
                   }

# index entities
import io
KB = 'dbpedia201604'  # dbpedia201604 or wikidata201809
file_name = "%s_terms" % KB  # file contains a list of 116,591,345 entity URIs with their frequencies in DBpedia KG
file_path = "../data/%s.txt" % file_name
ns_filter = "http://dbpedia.org/"  # process only entities with URIs from the DBpedia namespace 
index_name = '%se' % KB  # entities index

# iterate through input file in batches via streaming bulk
print("bulk indexing...")
try:
    for ok, response in streaming_bulk(es, actions=uris_stream(index_name, file_path, doc_type, ns_filter),
                                       chunk_size=100000):
        if not ok:
            # failure inserting
            print (response)
except TransportError as e:
    print(e.info)
    
print("Finished.")
