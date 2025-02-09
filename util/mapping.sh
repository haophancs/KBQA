curl -X PUT "localhost:9200/dbpedia201604e" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "default_analyzer": {
          "type": "custom",
          "tokenizer": "label_tokenizer",
          "filter": ["lowercase", "asciifolding"]
        },
        "snowball_analyzer": {
          "type": "custom",
          "tokenizer": "label_tokenizer",
          "filter": ["lowercase", "asciifolding", "snowball"]
        },
        "shingle_analyzer": {
          "type": "custom",
          "tokenizer": "label_tokenizer",
          "filter": ["shingle", "lowercase", "asciifolding"]
        },
        "ngram_analyzer": { 
          "type": "custom",
          "tokenizer": "ngram_tokenizer",
          "filter": ["lowercase", "asciifolding"]
        }
      },
      "tokenizer": {
        "label_tokenizer": {
          "type": "whitespace"
        },
        "ngram_tokenizer": {
          "type": "ngram",
          "min_gram": 3,
          "max_gram": 6,
          "token_chars": ["letter", "digit"]
        }
      }
    }
  },
  "mappings": {
    "terms": {
      "properties": {
        "label": {
          "type": "text",
          "fields": {
            "label": { "type": "text", "similarity": "BM25", "analyzer": "default_analyzer" },
            "snowball": { "type": "text", "similarity": "BM25", "analyzer": "snowball_analyzer" },
            "shingles": { "type": "text", "similarity": "BM25", "analyzer": "shingle_analyzer" },
            "ngrams": { "type": "text", "similarity": "BM25", "analyzer": "ngram_analyzer" }
          }   
        },
        "label_exact": { "type" : "keyword" },
        "uri": { "type" : "text" },
        "id": { "type" : "keyword" }
      }
    }
  }
}
'
