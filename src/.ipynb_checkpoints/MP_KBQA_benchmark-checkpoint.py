#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on Dec 9, 2018

.. codeauthor: svitlana vakulenko
    <svitlana.vakulenko@gmail.com>

Message Passing for KBQA
'''
import gc
import numpy as np

# connect to KG via HDT library
from hdt import HDTDocument
from enum import Enum
hdt_path = "/home/zola/Projects/hdt-cpp-molecules/libhdt/data/"
hdt_file = 'dbpedia2016-04en.hdt'
namespace = "http://dbpedia.org/"

# connect to indices
from index import IndexSearch
e_index = IndexSearch('dbpedia201604e')  # entity index
p_index = IndexSearch('dbpedia201604p')  # predicate index


# get a sample question from lcquad-train
from lcquad import load_lcquad

limit = 5000
samples = load_lcquad(fields=['corrected_question', 'entities', 'answers', 'sparql_template_id', '_id', 'sparql_query'],
                      dataset_split='train', shuffled=True, limit=limit)

# hold average stats for the model performance over the samples
ps, rs, fs = [], [], []

for sample in samples:
    question_o, correct_question_entities, answers, template_id, question_id, sparql_query = sample

    # skip questions with no answer found
    if not answers:
        continue

    print(question_id)

    # parse the SPARQL query into the sequence of predicate expansions
    tripple_patterns = sparql_query[sparql_query.find("{")+1:sparql_query.find("}")].split('. ')

    # collect entities and predicates separately for the intermediate nodes
    correct_intermediate_predicates = []
    correct_intermediate_entities = []
    correct_question_predicates = []
    correct_question_entities = []

    for pattern in tripple_patterns:
        if pattern:
            entities = []
            s, p, o = pattern.strip().split()
            if s[0] != '?':
                entities.append(s[1:-1])
            if o[0] != '?':
                entities.append(o[1:-1])
            p = p[1:-1]
            if '?uri' not in pattern:
                correct_intermediate_predicates.append(p)
                correct_intermediate_entities.extend(entities)
            else:
                correct_question_predicates.append(p)
                correct_question_entities.extend(entities)

    # get id of the answer entities
    answer_entities_ids = []
    for entity_uri in answers:
        matches = e_index.match_entities(entity_uri, match_by='uri')
        if matches:
            answer_entities_ids.append(matches[0]['_source']['id'])

    # assert len(answers) == len(answer_entities_ids)
    n_gs_answers = len(answer_entities_ids)


    # get a 2 hop subgraph

    # ! assume we know all correct entities and predicates
    # get entities and predicates for the 1st hop
    if correct_intermediate_predicates:
        top_entities, top_properties = correct_intermediate_entities, correct_intermediate_predicates
    else:
        top_entities, top_properties = correct_question_entities, correct_question_predicates
    
    top_entities = list(set(top_entities))
    top_properties = list(set(top_properties))

    # look up entities ids in index
    question_entities_ids1 = []
    # choose the least frequent entity for the seed
    entity_counts = []
    for entity_uri in top_entities:
        # if not in predicates check entities
        matches = e_index.match_entities(entity_uri, match_by='uri')
        if matches:
            question_entities_ids1.append(matches[0]['_source']['id'])
            entity_counts.append(int(matches[0]['_source']['count']))
        else:
            pass

    import numpy as np
    seed_entities = [question_entities_ids1[np.argmin(np.array(entity_counts))]]

    # look up entities ids in index for the 2nd hop
    if correct_intermediate_entities:
        # look up entities ids in index
        question_entities_ids2 = []
        for entity_uri in correct_question_entities:
            # if not in predicates check entities
            matches = e_index.match_entities(entity_uri, match_by='uri')
            if matches:
                question_entities_ids2.append(matches[0]['_source']['id'])
            else:
                pass
        seed_entities += question_entities_ids2

    predicates = correct_intermediate_predicates + correct_question_predicates

    kg = HDTDocument(hdt_path+hdt_file)
    kg.configure_hops(2, predicates, namespace, True)
    entities, predicate_ids, adjacencies = kg.compute_hops(seed_entities)
    kg.remove()
    # kg = None
    # del kg
    # gc.collect()

    # index entity ids global -> local
    entities_dict = {k: v for v, k in enumerate(entities)}

    # parse the subgraph into a sparse matrix
    import numpy as np
    import scipy.sparse as sp

    def generate_adj_sp(adjacencies, adj_shape, normalize=False, include_inverse=False):
        # colect all predicate matrices separately into a list
        sp_adjacencies = []
        for edges in adjacencies:
            # split subject (row) and object (col) node URIs
            n_edges = len(edges)
            row, col = np.transpose(edges)
            
            # duplicate edges in the opposite direction
            if include_inverse:
                _row = np.hstack([row, col])
                col = np.hstack([col, row])
                row = _row
                n_edges *= 2
            
            # create adjacency matrix for this predicate TODO initialise matrix with predicate scores
            data = np.ones(n_edges, dtype=np.int8)
            adj = sp.csr_matrix((data, (row, col)), shape=adj_shape, dtype=np.int8)
            
            if normalize:
                adj = normalize_adjacency_matrix(adj)

            sp_adjacencies.append(adj)
        
        return np.asarray(sp_adjacencies)

            
    adj_shape = (len(entities), len(entities))
    # generate a list of adjacency matrices per predicate assuming the graph is undirected wo self-loops
    A = generate_adj_sp(adjacencies, adj_shape, include_inverse=True)
    # garbage collection
    # del adjacencies
    # gc.collect()

    # ## Message Passing

    # initial activations of entities
    # look up local entity id
    q_ids = [entities_dict[entity_id] for entity_id in question_entities_ids1 if entity_id in entities_dict]
    # graph activation vector TODO activate with the scores
    X1 = np.zeros(len(entities))
    X1[q_ids] = 1


    # 1 hop
    # ! assume we know the correct predicate sequence activation
    # look up ids in index
    top_p_ids = []
    for p_uri in top_properties:
        # if not in predicates check entities
        matches = p_index.match_entities(p_uri, match_by='uri')
        if matches:
            top_p_ids.append(matches[0]['_source']['id'])
        else:
            print ("%s not found" % p_uri)

    p_ids = [i for i, p_id in enumerate(predicate_ids) if p_id in top_p_ids]

    # collect activations
    Y1 = np.zeros(len(entities))
    activations1 = []

    n_p = len(p_ids)
    n_e = len(entities)

    # slice A by the selected predicates and concatenate edge lists
    Y1 = (X1 * sp.hstack(A[p_ids])).reshape([n_p, n_e]).sum(0)
    
    # slice A
    # for a_p in A[p_ids]:
    #     # activate current adjacency matrix via input propagation
    #     y_p = X1 * a_p
    #     # check if there is any signal through
    #     if sum(y_p) > 0:
    #         # add up activations
    #         Y1 += y_p

    # check output size
    assert Y1.shape[0] == len(entities)

    # normalize activations by checking the 'must' constraints: number of constraints * weights
    Y1 -= (len(q_ids) - 1) * 1

    # check activated entities
    # n_activated = len(np.argwhere(Y1 > 0))
    top = np.argwhere(Y1 > 0).T.tolist()[0]
    n_answers = len(top)

    # draw top activated entities from the distribution
    if n_answers:
        # top = Y1.argsort()[-n_answers:][::-1]
        activations1 = np.asarray(entities)[top]
        # n_answers = len(activations1)

    # garbage collection
    # del Y1, X1, a_p, p_ids
    # gc.collect()


    # 2 hop
    # check if we need the second hop to cover the remaining predicates and entities
    activations2 = []

    if correct_intermediate_predicates:
        # get next 1-hop subgraphs for all activated entities and the remaining predicates
        # choose properties for the second hop
        top_properties2 = correct_question_predicates
        
        # propagate activations
        X2 = np.zeros(len(entities))

        # activate entities selected at the previous hop and question entities activations for the 2nd hop
        top_entities2 = activations1.tolist()
        
        # look up local entity id
        a_ids2 = [entities_dict[int(entity_id)] for entity_id in top_entities2 if entity_id in entities_dict]
        # graph activation vector
        X2[a_ids2] = 1

        # look up local entity id
        a_ids_q = [entities_dict[entity_id] for entity_id in question_entities_ids2 if entity_id in entities_dict]
        # graph activation vector
        X2[a_ids_q] = len(a_ids2)

        # ! assume we know the correct predicate sequence activation
        # look up ids in index
        top_p_ids2 = []
        for p_uri in top_properties2:
            # if not in predicates check entities
            matches = p_index.match_entities(p_uri, match_by='uri')
            if matches:
                top_p_ids2.append(matches[0]['_source']['id'])
            else:
                print ("%s not found" % p_uri)
        
        # get indices of the predicates for this hop
        p_ids = [i for i, p_id in enumerate(predicate_ids) if p_id in top_p_ids2]
       
        # collect activations
        Y2 = np.zeros(len(entities))
        
        n_p = len(p_ids)

        # slice A by the selected predicates and concatenate edge lists
        Y2 = (X2 * sp.hstack(A[p_ids])).reshape([n_p, n_e]).sum(0)
        # # activate adjacency matrices per predicate
        # # slice A
        # for a_p in A[p_ids]:
        #     # propagate from the previous activation layer
        #     y_p = X2*a_p
        #     # check if there is any signal through
        #     if sum(y_p) > 0:
        #         # add up activations
        #         Y2 += y_p
        
        # normalize activations by checking the 'must' constraints: number of constraints * weights
        Y2 -= len(a_ids_q) * len(a_ids2)
        
        # check output size
        assert Y2.shape[0] == len(entities)

        # check activated entities
        # n_activated = len(np.argwhere(Y2 > 0))
        top = np.argwhere(Y2 > 0).T.tolist()[0]
        n_answers = len(top)

        # draw top activated entities from the distribution
        if n_answers:
            # top = Y2.argsort()[-n_answers:][::-1]
            activations2 = np.asarray(entities)[top]
            # n_answers = len(activations2)

        # garbage collection
        # del Y2, X2, a_p, p_ids
        # gc.collect()


    # translate correct answers ids to local subgraph ids
    a_ids = [entities_dict[entity_id] for entity_id in answer_entities_ids if entity_id in entities_dict]
    
    # garbage collection
    # del A, entities, entities_dict, predicate_ids
    # gc.collect()

    n_correct = len(set(top) & set(a_ids))

    # report on error
    if n_correct != n_gs_answers:
        print("!%d/%d"%(n_correct, n_gs_answers))

    # recall: answers that are correct / number of correct answers
    r = float(n_correct) / n_gs_answers    

    if n_answers > 0:
        # precision: answers that are correct / number of answers
        p = float(n_correct) / n_answers
        # f-measure
        f = 2 * p * r / (p + r)
    else:
        p = 0
        f = 0

    # add stats
    ps.append(p)
    rs.append(r)
    fs.append(f)


print("P: %.2f R: %.2f F: %.2f"%(np.mean(ps), np.mean(rs), np.mean(fs)))
print("Fin. Results for %d questions"%len(ps))
