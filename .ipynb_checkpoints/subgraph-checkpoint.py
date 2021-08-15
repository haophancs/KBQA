#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on Nov 26, 2018

.. codeauthor: svitlana vakulenko
    <svitlana.vakulenko@gmail.com>

Crawl GS subgraph for each question from DBpedia HDT
'''
from subprocess import call, Popen, PIPE

from lcquad import load_lcquad
from index import IndexSearch


limit = 10

# get a random sample of questions from lcquad train split
samples = load_lcquad(fields=['corrected_question', 'entities', 'answers'], dataset_split='train',
                      shuffled=True, limit=limit)

es = IndexSearch()
# interate over questions entities dataset
for question, correct_question_entities, answers in samples:
    print (correct_question_entities)
    # pick a seed entity for each question
    matched_uris = []
    matched_ids = []
    # add answer entities
    correct_question_entities.extend(answers)
    for entity_uri in correct_question_entities:
        matches = es.match_entities(entity_uri, match_by='uri')
        # p
        if len(matches) > 1:
            for match in matches:
                if match['_source']['term_type'] == "predicates":
                    matched_ids.append(match['_source']['id'])
        # s o
        elif matches:
            matched_uris.append(matches[0]['_source']['uri'])
            matched_ids.append(matches[0]['_source']['id'])


    print (matched_uris)
    print (matched_ids)

    # request subgraph from the API (2 hops from the seed entity)
    # /home/zola/Projects/hdt-cpp-molecules/libhdt/tools/hops -t "<http://dbpedia.org/resource/David_King-Wood>" -p "http://dbpedia.org/" -n 2 /home/zola/Projects/hdt-cpp-molecules/libhdt/data/dbpedia2016-04en.hdt
    hdt_lib_path = "/home/zola/Projects/hdt-cpp-molecules/libhdt"
    p = Popen(["/home/zola/Projects/hdt-cpp-molecules/libhdt/tools/hops", "-t", "<%s>"%matched_uris[0], '-p', "http://dbpedia.org/", '-n', '2', 'data/dbpedia2016-04en.hdt'], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=hdt_lib_path)
    subgraph, err = p.communicate()
    # print (subgraph)

    # parse subgraph triples
    # entities = []
    # predicates = []
    terms = []
    for triple in subgraph.split('\n'):
        # print (triple)
        terms.extend(triple.split())
        # s, p, o = terms
        # entities.append(s)
        # predicates.append(p)
        # entities.append(o)
    terms = set(terms)
    # print terms
    # verify subgraph, i.e. all question entities are within the extracted subgraph
    for term_id in matched_ids:
        if str(term_id) not in terms:
            print "%s not found in the extracted subgraph" % term_id
