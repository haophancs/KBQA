#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on Nov 8, 2019

.. codeauthor: svitlana vakulenko
    <svitlana.vakulenko@gmail.com>

Functions to load pre-trained models for KBQA
'''

from keras.models import Model, Input
from keras.layers import LSTM, Embedding, Dense, Bidirectional, TimeDistributed
from keras.optimizers import *


# define bi-LSTM model architecture (loose embeddings layer to do on-the-fly embedding at inference time)
def build_qt_inference_model(model_settings):
    # architecture
    _input = Input(shape=(model_settings['max_len'], model_settings['emb_dim']), name='input')
    model = Bidirectional(LSTM(units=100, return_sequences=True, dropout=0.5,
                               recurrent_dropout=0.5), name='bilstm1')(_input)  # biLSTM
    model = Bidirectional(LSTM(units=100, return_sequences=False, dropout=0.5,
                               recurrent_dropout=0.5), name='bilstm2')(model)  # 2nd biLSTM
    _output = Dense(model_settings['n_tags'], activation='softmax', name='output')(model)  # a dense layer
    model = Model(_input, _output)
    model.compile(optimizer=Nadam(clipnorm=1), loss='categorical_crossentropy', metrics=['accuracy']) 
    model.summary()
    return model

# load pre-trained EP spans parsing network
modelname = '2hops-types'

from keras_contrib.layers import CRF
from keras_contrib import losses, metrics


# prediction time span generator
def collect_mentions(words, y_p, tag_ind):
    e_span, e_spans = [], []
    for w, pred in zip(words, y_p):
        if pred == tag_ind:
            e_span.append(w)
        elif e_span:
            e_spans.append(" ".join(e_span))
            e_span = []
    # add last span
    if e_span:
        e_spans.append(" ".join(e_span))
        e_span = []
    # remove duplicates
    return list(set(e_spans))


# define bi-LSTM model architecture (loose embeddings layer to do on-the-fly embedding at inference time)
def build_ep_inference_model(model_settings):
    # architecture
    input = Input(shape=(model_settings['max_len'], model_settings['emb_dim']), name='input')
    model = Bidirectional(LSTM(units=100, return_sequences=True), name='bilstm1')(input)  # biLSTM
    model = Bidirectional(LSTM(units=100, return_sequences=True), name='bilstm2')(model)  # 2nd biLSTM
    model = TimeDistributed(Dense(model_settings['n_tags'], activation=None), name='td')(model)  # a dense layer
    crf = CRF(model_settings['n_tags'], name='crf')  # CRF layer
    out = crf(model)  # output
    model = Model(input, out)
    model.compile(optimizer=Nadam(lr=0.01, clipnorm=1), loss=losses.crf_loss, metrics=[metrics.crf_accuracy]) 
    model.summary()
    return model


import re, string

def preprocess_span(span):
    entity_label = " ".join(re.sub('([a-z])([A-Z])', r'\1 \2', span).split())
    words = entity_label.split('_')
    unique_words = []
    for word in words:
        # strip punctuation
        word = "".join([c for c in word if c not in string.punctuation])
        if word:
            word = word.lower()
            if word not in unique_words:
                unique_words.append(word)
    return " ".join(unique_words)

