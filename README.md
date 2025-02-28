# Analyzing How BERT Performs Entity Matching
State-of-the-art Entity Matching (EM) approaches rely on transformer architectures, such as *BERT*, for generating  highly contextualized embeddings of terms. The embeddings  are then used to predict whether pairs of entity descriptions refer to the same real-world entity. BERT-based EM models demonstrated to be effective, but act as black-boxes for the users, who have limited insight into the motivations behind their decisions.
In this repo, we perform a multi-facet analysis of the components of pre-trained and fine-tuned BERT architectures applied to an EM task.

For a detailed description of the work please read [our paper](https://www.vldb.org/pvldb/vol15/p1726-paganelli.pdf). Please cite the paper if you use the code from this repository in your work.

```
@article{DBLP:journals/pvldb/PaganelliBBG22,
  author    = {Matteo Paganelli and
               Francesco Del Buono and
               Andrea Baraldi and
               Francesco Guerra},
  title     = {Analyzing How {BERT} Performs Entity Matching},
  journal   = {Proc. {VLDB} Endow.},
  volume    = {15},
  number    = {8},
  pages     = {1726--1738},
  year      = {2022}
}
```

## Library

### Requirements

- Python: Python 3.*
- Packages: requirements.txt

### Installation

```bash
$ virtualenv -p python3 venv

$ source venv/bin/activate

$ pip install -r requirements.txt

```

## Experiments

### Create BERT-based EM models
This means to create a binary classifier on top of the BERT model.
For purely demonstrative purposes, below we will train the EM model only on the dataset Structured_Fodors-Zagats.

**Option 1**: pre-trained EM model. Only the classification layer is fine-tuned on the EM task.
```python
  python -m utils.bert_em_pretrain --use_cases Structured_Fodors-Zagats --tok sent_pair --experiment compute_features
  python -m utils.bert_em_pretrain --use_cases Structured_Fodors-Zagats --tok sent_pair --experiment train
```

**Option 2**: fine-tuned EM model. Both the BERT architecture and the classification layer are fine-tuned on the EM task.
```python
  python -m utils.bert_em_fine_tuning --fit True --use_cases Structured_Fodors-Zagats --tok sent_pair
```
The model will be stored in the directory *results/models/*.

### Experiment Sec. 4.1 (Tab. 2)
Pre-trained EM model
```python
  python -m utils.bert_em_pretrain --use_cases all --tok sent_pair --experiment eval
  python -m utils.bert_em_pretrain --use_cases all --tok attr_pair --experiment eval
```
	
Fine-tuned EM model
```python
  python -m utils.bert_em_fine_tuning --fit False --use_cases all --tok sent_pair
  python -m utils.bert_em_fine_tuning --fit False --use_cases all --tok attr_pair
```

### Experiment Sec. 4.2 (Fig. 1)
```python
  python -m experiments.fine_tuning_impact_on_attention.py --use_cases all
```

### Experiment Sec. 4.3 (Fig. 2)
```python
  python -m experiments.fine_tuning_impact_on_embeddings.py --use_cases all
```

### Experiment Sec. 5.1 (Fig. 3)	
Prerequisites
```python
  python -m experiments.get_attention_weights.py --use_cases all --multi_process True --attn_extractor token_extractor --special_tokens True --agg_metric mean --fine_tune False	
  python -m experiments.get_attention_weights.py --use_cases all --multi_process True --attn_extractor token_extractor --special_tokens True --agg_metric mean --fine_tune True
```

Run the experiment
```python
  python -m experiments.e2e_attention.py --use_cases Structured_Amazon-Google Structured_Beer Textual_Abt-Buy Dirty_Walmart-Amazon --experiment comparison --comparison tune --small_plot True
  python -m experiments.e2e_attention.py --use_cases Structured_Amazon-Google Structured_Beer Textual_Abt-Buy Dirty_Walmart-Amazon --fine_tune True --experiment simple --small_plot True
```

### Experiment Sec. 5.2 (Fig. 4)
Prerequisites
```python
  python -m experiments.attention.analyze_attention_weights.py --use_cases all --attn_extractor attr_extractor --agg_metric max --fine_tune False --attn_tester attr_tester
```

Run the experiment
```python
  python -m experiments.attention.attention_test.py --use_cases all --attn_extractor attr_extractor --agg_metric max --fine_tune False --attn_tester attr_tester --analysis_target benchmark --analysis_type multi --plot_params attr_attn_3_last
```

### Experiment Sec. 5.2 (Fig. 5)
Prerequisites
```python
  python -m experiments.attention.analyze_attention_weights.py --use_cases all --attn_extractor attr_extractor --agg_metric mean --fine_tune False --tok sent_pair --attn_tester attr_pattern_tester
  python -m experiments.attention.analyze_attention_weights.py --use_cases all --attn_extractor attr_extractor --agg_metric mean --fine_tune False --tok attr_pair --attn_tester attr_pattern_tester
  python -m experiments.attention.analyze_attention_weights.py --use_cases all --attn_extractor attr_extractor --agg_metric mean --fine_tune True --tok sent_pair --attn_tester attr_pattern_tester
  python -m experiments.attention.analyze_attention_weights.py --use_cases all --attn_extractor attr_extractor --agg_metric mean --fine_tune True --tok attr_pair --attn_tester attr_pattern_tester
```

Run the experiment
```python
  python -m experiments.attention.attention_patterns.py --use_cases all --attn_extractor attr_extractor --agg_metric mean --attn_tester attr_pattern_tester --experiment all_freq --analysis_type comparison --comparison_param tune_tok
```

### Experiment Sec. 5.2.1 (Fig. 6)
Prerequisites
```python
  python -m experiments.attention.analyze_attention_weights.py --use_cases all --attn_extractor attr_extractor --agg_metric mean --fine_tune False --tok sent_pair --attn_tester attr_pattern_tester
  python -m experiments.attention.analyze_attention_weights.py --use_cases all --attn_extractor attr_extractor --agg_metric mean --fine_tune True --tok sent_pair --attn_tester attr_pattern_tester
```

Run the experiment
```python
  python -m experiments.attention.attention_patterns.py --use_cases all --attn_extractor attr_extractor --agg_metric mean --attn_tester attr_pattern_tester --experiment match_freq_by_layer --analysis_type comparison --comparison_param tune
```

### Experiment Sec. 5.2.1 (Fig. 7)
Prerequisites
```python
  python -m experiments.attention.analyze_attention_weights.py --use_cases all --attn_extractor attr_extractor --agg_metric max --fine_tune True --attn_tester attr_tester
```

Run the experiment
```python
  python -m experiments.attention.attention_head_pruning.py --use_cases all --attn_extractor attr_extractor --agg_metric max --attn_tester attr_tester --task compute --prune_or_mask_methods importance maa random --prune_or_mask_amounts 5 10 20 50 100 --prune True
  python -m experiments.attention.attention_head_pruning.py --use_cases all --attn_extractor attr_extractor --agg_metric max --attn_tester attr_tester --task visualize --prune_or_mask_methods importance maa random --prune_or_mask_amounts 5 10 20 50 100 --prune True
```

### Experiment Sec. 5.3.1 (Fig. 8)
Prerequisites
```python
  python -m experiments.attention.get_attention_weights.py --use_cases all --multi_process True --attn_extractor attr_extractor --special_tokens True --agg_metric max --fine_tune True
  python -m experiments.attention.get_attention_weights.py --use_cases all --multi_process True --attn_extractor attr_extractor --special_tokens True --agg_metric max --fine_tune False
```

Run the experiment
```python
  python -m experiments.attention.cls_to_attr_attention.py --use_cases Structured_Fodors-Zagats Structured_DBLP-GoogleScholar Structured_DBLP-ACM Dirty_DBLP-ACM --attn_extractor attr_extractor --agg_metric max --experiment comparison --comparison tune --small_plot True
  python -m experiments.attention.cls_to_attr_attention.py --use_cases Structured_Fodors-Zagats Structured_DBLP-GoogleScholar Structured_DBLP-ACM Dirty_DBLP-ACM --attn_extractor attr_extractor --agg_metric max --experiment simple --small_plot True --fine_tune True --data_categories all_pos all_neg
```

### Experiment Sec. 5.3.2 (Fig. 9)
Prerequisites
```python
  python -m experiments.gradient.get_grads.py --use_cases all --grad_text_units attrs --multi_process True
```

Run the experiment
```python
  python -m experiments.gradient.plot_grads.py --use_cases all --grad_text_units attrs
```

### Experiment Sec. 6.1 (Fig. 10)
Prerequisites

Download the **fasttext** embeddings (*wiki-news-300d-1M*) from [here](https://fasttext.cc/docs/en/english-vectors.html) and save them in the data folder.

```python
  python -m experiments.get_attention_weights.py --use_cases all --multi_process True --attn_extractor word_extractor --special_tokens True --agg_metric mean --fine_tune False
  python -m experiments.get_attention_weights.py --use_cases all --multi_process True --attn_extractor word_extractor --special_tokens True --agg_metric mean --fine_tune True
```

Run the experiment
```python
  python -m experiments.attention_to_similar_words.py --use_cases all --sim_metric cosine --sem_embs fasttext --fine_tune False --task compute
  python -m experiments.attention_to_similar_words.py --use_cases all --sim_metric cosine --sem_embs fasttext --fine_tune True --task compute
  python -m experiments.attention_to_similar_words.py --use_cases all --sim_metric cosine --task visualize
```

### Experiment Sec. 6.2 (Fig. 11)
(Optional) Prerequisites

Download the **fasttext** embeddings (*wiki-news-300d-1M*) from [here](https://fasttext.cc/docs/en/english-vectors.html) and save them in the data folder.

If the experiment in Sec. 4.3 has been run with the flag *--save_embs*, in the following experiment we can avoid re-computing the embeddings by specifying the option *--precomputed_embs True*

Run the experiment
```python
  python -m experiments.emb_sym_analysis.py --use_cases all --sim_metric cosine --sem_embs fasttext --fine_tune False --task compute
  python -m experiments.emb_sym_analysis.py --use_cases all --sim_metric cosine --sem_embs fasttext --fine_tune True --task compute
  python -m experiments.emb_sym_analysis.py --use_cases all --sim_metric cosine --task visualize
```

### Experiment Sec. 6.3 (Fig. 12)
Prerequisites

Download the **fasttext** embeddings (*wiki-news-300d-1M*) from [here](https://fasttext.cc/docs/en/english-vectors.html) and save them in the data folder.

```python
  python -m experiments.gradient.get_grads.py --use_cases all --grad_text_units words --multi_process True
```

Run the experiment
```python
  python -m experiments.gradient.gradient_embeddings_comparison.py --use_cases all --grad_text_units words --sim_metric cosine --sem_embs fasttext --task compute
  python -m experiments.gradient.gradient_embeddings_comparison.py --use_cases all --grad_text_units words --sim_metric cosine --sem_embs fasttext --task visualize
```

## License
[MIT License](LICENSE)
