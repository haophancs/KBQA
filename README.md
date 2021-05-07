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
docker run --gpus all -it --entrypoint bash -v /home/tamnguyen/tvk/mpqa:/mpqa nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04
cd /mpqa
apt update && apt -y upgrade
apt install -y wget git curl unzip tmux vim
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

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
cd /mpqa
git clone https://github.com/rdfhdt/hdt-cpp
cd hdt-cpp
apt install -y autoconf libtool zlib1g zlib1g-dev pkg-config libserd-0-0 libserd-dev
./autogen.sh
./configure
make -j16
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
cd /mpqa
mkdir indexing && cd indexing
wget http://fragments.dbpedia.org/hdt/dbpedia2016-04en.hdt
wget http://fragments.dbpedia.org/hdt/dbpedia2016-04en.hdt.index.v1-1
hdt-cpp/libhdt/tests/dumpDictionary dbpedia2016-04en.hdt -o -t dbpedia201604_terms.txt
hdt-cpp/libhdt/tests/dumpDictionary dbpedia2016-04en.hdt -p dbpedia201604_predicates.txt
```

4. Install ElasticSearch 
```
apt install -y openjdk-8-jdk
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
apt install -y apt-transport-https
echo "deb https://artifacts.elastic.co/packages/5.x/apt stable main" | tee -a /etc/apt/sources.list.d/elastic-5.x.list
apt update && apt install -y elasticsearch=5.5.3
service elasticsearch start
```

5. Index entities and predicates into ElasticSearch
```
cd /mpqa/KBQA/util
python index.py
```

6. Download LC-QuAD dataset from http://lc-quad.sda.tech
```
cd /mpqa
mkdir ./lcquad
wget https://raw.githubusercontent.com/AskNowQA/LC-QuAD/data/train-data.json
wget https://raw.githubusercontent.com/AskNowQA/LC-QuAD/data/test-data.json
```

7. Install MongoDB, import LC-QuAD dataset into MongoDB
```
mkdir /mpqa/db
mkdir /mpqa/db/mongod.log
mongod --dbpath /mpqa/db --fork --logpath /mpqa/db/log
mongo
use mpqa
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

see notebooks

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