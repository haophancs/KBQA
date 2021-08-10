# MPqa

[Svitlana Vakulenko, Javier D. Fernandez, Axel Polleres, Maarten de Rijke and Michael Cochez. Message Passing for Complex Question Answering over Knowledge Graphs. CIKM. 2019](https://arxiv.org/abs/1908.06917)


## Requirements

* Python 3.6
* tensorflow==1.11.0
* keras==2.2.4

* pyHDT (for accesssing the DBpedia Knowledge Graph)
* elasticsearch==5.5.3 (for indexing entities and predicate labels of the Knowledge Graph)

* pymongo (for storing the LC-QuAD dataset)
* flask (for the API)


## Datasets

* [LCQUAD](http://lc-quad.sda.tech) 5,000 pairs of questions and SPARQL queries

## Setup

1. Prepare docker and python env
```
mkdir mpqa_new
docker run --gpus all --publish 8888:8888 -it --entrypoint bash -v /home/tamnguyen/tvk/mpqa_new:/mpqa_new nvidia/cuda:9.0-cudnn7-devel-ubuntu16.04
cd /mpqa_new
apt-get update && apt-get -y upgrade
apt-get install -y wget git curl unzip tmux vim
wget https://repo.anaconda.com/miniconda/Miniconda3-py37_4.10.3-Linux-x86_64.sh
bash Miniconda3-py37_4.10.3-Linux-x86_64.sh

# Now restart container
git clone https://github.com/haophancs/KBQA/
cd KBQA
conda create -n kbqa python=3.6 pip -y
conda activate kbqa
pip install -r requirements.txt
```

2. Install HDT
 - HDT-CPP:
```
cd /mpqa_new
git clone https://github.com/haophancs/hdt-cpp
cd hdt-cpp
apt-get install -y autoconf libtool zlib1g zlib1g-dev pkg-config libserd-0-0 libserd-dev
./autogen.sh
./configure
make -j32
make install
cd ./libhdt/tests/
make check
```
 - HDT API:
```
pip install pybind11==2.2.4
pip install hdt==2.2.1
```

3. Download DBPedia 2016-04 English HDT file and its index from http://www.rdfhdt.org/datasets/
```
cd /mpqa_new
mkdir indexing && cd indexing
wget http://fragments.dbpedia.org/hdt/dbpedia2016-04en.hdt
wget http://fragments.dbpedia.org/hdt/dbpedia2016-04en.hdt.index.v1-1
../hdt-cpp/libhdt/tests/dumpDictionary dbpedia2016-04en.hdt -o -t dbpedia201604_terms.txt
../hdt-cpp/libhdt/tests/dumpDictionary dbpedia2016-04en.hdt -p dbpedia201604_predicates.txt
```

4. Install ElasticSearch 
```
apt-get install -y openjdk-8-jdk
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
apt-get install -y apt-get-transport-https
echo "deb https://artifacts.elastic.co/packages/5.x/apt stable main" | tee -a /etc/apt/sources.list.d/elastic-5.x.list
apt-get update && apt-get install -y elasticsearch=5.5.3
service elasticsearch start
pip uninstall elasticsearch
pip install elasticsearch==5.5.3
```
  Change data directory of Elasticsearch
 - ```mkdir /mpqa_new/elasticsearch/```
 - Open ```/etc/elasticsearch/elasticsearch.yml```, set ```path.data```: ```/mpqa_new/elasticsearch/``` 
 - Open ```/etc/init.d/elasticsearch```, set ```DATA_DIR=/mpqa_new/$NAME```
 - Run ```chown -R elasticsearch:elasticsearch /mpqa_new/elasticsearch/```

5. Index entities and predicates into ElasticSearch
```
cd /mpqa_new/KBQA/util
python3 index.py terms
python3 index.py predicates
```

6. Download dataset and embeddings
   
- LC-QUAD
```
wget https://raw.githubusercontent.com/AskNowQA/LC-QuAD/data/train-data.json -P /mpqa_new/KBQA/data/lcquad
wget https://raw.githubusercontent.com/AskNowQA/LC-QuAD/data/test-data.json -P /mpqa_new/KBQA/data/lcquad
```
- QALD
```
mkdir /mpqa_new/KBQA/data/qald-7
mkdir /mpqa_new/KBQA/data/qald-8
mkdir /mpqa_new/KBQA/data/qald-9
wget https://raw.githubusercontent.com/ag-sc/QALD/master/7/data/qald-7-train-multilingual.json -P /mpqa_new/KBQA/data/qald-7
wget https://raw.githubusercontent.com/ag-sc/QALD/master/7/data/qald-7-test-multilingual.json -P /mpqa_new/KBQA/data/qald-7
wget https://raw.githubusercontent.com/ag-sc/QALD/master/8/data/qald-8-train-multilingual.json -P /mpqa_new/KBQA/data/qald-8
wget https://raw.githubusercontent.com/ag-sc/QALD/master/8/data/qald-8-test-multilingual.json -P /mpqa_new/KBQA/data/qald-8
wget https://raw.githubusercontent.com/ag-sc/QALD/master/9/data/qald-9-train-multilingual.json -P /mpqa_new/KBQA/data/qald-9
wget https://raw.githubusercontent.com/ag-sc/QALD/master/9/data/qald-9-test-multilingual.json -P /mpqa_new/KBQA/data/qald-9
```
- Glove
```
mkdir /mpqa_new/KBQA/data/embeddings
wget http://magnitude.plasticity.ai/glove/heavy/glove.6B.100d.magnitude -P /mpqa_new/KBQA/data/embeddings
```

7. Install and run MongoDB service:

   Follow this guide: https://www.digitalocean.com/community/tutorials/how-to-install-mongodb-on-ubuntu-18-04-source
```
mkdir /mpqa_new/db
mkdir /mpqa_new/db/mongod.log
mongod --dbpath /mpqa_new/db --fork --logpath /mpqa_new/db/log
```


<!-- 
2. Download and make [fastText](https://github.com/facebookresearch/fastText), load the English model trained on Wikipedia and generate fastText embeddings:

'''
cd data
wget https://s3-us-west-1.amazonaws.com/fasttext-vectors/wiki.en.zip
unzip wiki.en.zip
rm wiki.en.zip
'''

./fasttext print-word-vectors ../KBQA/data/fasttext/wiki.en.bin < ../KBQA/data/test_question_words.txt > ../KBQA/data/test_question_words_fasttext.txt

 -->


## Run
Install jupyter

Follow this guide to run jupyter with ngrok https://towardsdatascience.com/how-to-share-your-jupyter-notebook-in-3-lines-of-code-with-ngrok-bfe1495a9c0c

Run command: ```jupyter notebook --no-browser --ip=0.0.0.0 --port=8888 --allow-root```

See notebooks

**Attention:** We have not imported dataset into MongoDB, follow the 0_preprocessing.ipynb first, set the variable **loaded = False** (it's True by default) to import data

## Benchmark

python final_benchmark_results.py

## Citation

```bibtex
@inproceedings{DBLP:conf/cikm/VakulenkoGPRC19,
  author    = {Svitlana Vakulenko and
               Javier David Fernandez Garcia and
               Axel Polleres and
               Maarten de Rijke and
               Michael Cochez},
  title     = {Message Passing for Complex Question Answering over Knowledge Graphs},
  booktitle = {Proceedings of the 28th {ACM} International Conference on Information
               and Knowledge Management, {CIKM} 2019, Beijing, China, November 3-7,
               2019},
  pages     = {1431--1440},
  year      = {2019},
  url       = {https://doi.org/10.1145/3357384.3358026},
  doi       = {10.1145/3357384.3358026},
  timestamp = {Mon, 04 Nov 2019 11:09:32 +0100}
}
```
