import logging
import os
import pickle
import re

import gensim
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import utils.nlp as nlp


def get_sent_word_idxs(offsets: list):
    """
    This function returns the indexes of the words included in a sentence tokenized with BERT.

    :param offsets: offset_mapping parameter extracted from a BERT tokenizer
    :return: list of tuples that indicate the start end indexes of a word in a BERT-tokenized sentence
    """

    assert isinstance(offsets, list), "offsets param is not a list."
    assert len(offsets) > 0, "Empty offsets."

    # aggregate all tokens of the sentence that refer to the same word
    # these tokens can be detected by searching for adjacent offsets from the
    # `offset_mapping` parameter
    tokens_to_sent_offsets = offsets[:]
    tokens_by_word = []  # this list will aggregate the token offsets by word
    prec_token_offsets = None
    tokens_in_word = []  # this list will accumulate all the tokens that refer to a target word
    words_offsets = []  # this list will store for each word the range of token idxs that refer to it
    for ix, token_offsets in enumerate(tokens_to_sent_offsets):

        # special tokens (e.g., [CLS], [SEP]) do not refer to any words
        # their offsets are equal to (0, 0)
        if token_offsets == [0, 0]:

            # save all the tokens that refer to the previous word
            if len(tokens_in_word) > 0:
                l = int(np.sum([len(x) for x in tokens_by_word]))
                words_offsets.append((l, l + len(tokens_in_word)))
                tokens_by_word.append(tokens_in_word)
                prec_token_offsets = None
                tokens_in_word = []

            l = int(np.sum([len(x) for x in tokens_by_word]))
            # words_offsets.append((l, l + 1))
            tokens_by_word.append([token_offsets])
            continue

        if prec_token_offsets is None:
            tokens_in_word.append(token_offsets)
        else:
            # if the offsets of the current and previous tokens are adjacent then they
            # refer to the same word
            if prec_token_offsets[1] == token_offsets[0]:
                tokens_in_word.append(token_offsets)
            else:
                # the current token refers to a new word

                # save all the tokens that refer to the previous word
                l = int(np.sum([len(x) for x in tokens_by_word]))
                words_offsets.append((l, l + len(tokens_in_word)))
                tokens_by_word.append(tokens_in_word)

                tokens_in_word = [token_offsets]

        prec_token_offsets = token_offsets

    # Note that 'words_offsets' contains only real word offsets, i.e. offsets
    # for special tokens (e.g., [CLS], [SEP], [PAD]), except for the [UNK]
    # token, are omitted

    return words_offsets


def get_sent_pair_word_idxs(sent1: str, sent2: str, tokenizer, max_len: int):
    """
    This function returns the indexes of the words included in a pair of sentences tokenized with BERT.

    :param sent1: first sentence
    :param sent2: second sentence
    :param tokenizer: BERT tokenizer
    :param max_len: max number of tokens included in the sentence pair
    :return: (sentence 1 word indexes, sentence 2 word indexes, tokens)
    """

    encoded_pair_sent = tokenizer(sent1, sent2, padding='max_length', truncation=True,
                                  return_tensors="pt", max_length=max_len,
                                  add_special_tokens=True, pad_to_max_length=True,
                                  return_attention_mask=False,
                                  return_offsets_mapping=True)

    tokens = tokenizer.convert_ids_to_tokens(encoded_pair_sent['input_ids'][0])

    # split the offset mappings at sentence level by exploting the [SEP] which
    # is identified with the offsets [0, 0] (as any other special tokens)
    offsets = encoded_pair_sent['offset_mapping'].squeeze(0).tolist()
    sep_idx = offsets[1:].index([0, 0])  # ignore the [CLS] token at the index 0
    left_offsets = offsets[:sep_idx + 2]
    right_offsets = offsets[sep_idx + 1:]

    left_word_idxs = get_sent_word_idxs(left_offsets)
    right_word_idxs = get_sent_word_idxs(right_offsets)

    return left_word_idxs, right_word_idxs, tokens


def get_entity_pair_attr_idxs(left_entity: pd.Series, right_entity: pd.Series, tokenizer, max_len: int):
    """
    This function returns the indexes of the attributes included in a pair of entities tokenized with BERT.
    Optionally the function can return also the word or token indexes.

    :param left_entity: Pandas' Series object containing the data of the first entity
    :param right_entity: Pandas' Series object containing the data of the second entity
    :param tokenizer: BERT tokenizer
    :param max_len: max number of tokens included in the sentence pair
    :return: dictionary containing data about attribute/word/token indexes for the input pair of entities
    """

    def _check_attr_idxs_consistency(left_idxs: list, right_idxs: list, tokens: list, num_attrs: int, max_len: int):

        left_trunc = False
        right_trunc = False
        assert len(left_idxs) == num_attrs
        assert len(right_idxs) == num_attrs
        assert left_idxs[0][0] == 1  # ignore [CLS] token

        # check left attribute indexes consistency
        sep_idx = tokens.index('[SEP]')
        last_left_valid_attr = None
        idx = 0
        while last_left_valid_attr is None:
            last_left_valid_attr = left_idxs[-(1 + idx)]
            idx += 1
        assert last_left_valid_attr[1] == sep_idx
        if idx > 1:
            left_trunc = True

        assert last_left_valid_attr[1] + 1 == right_idxs[0][0]  # ignore [SEP] token

        # check right attribute indexes consistency
        last_sep_idx = tokens[sep_idx + 1:].index('[SEP]') + sep_idx + 1
        last_right_valid_attr = None
        idx = 0
        while last_right_valid_attr is None:
            last_right_valid_attr = right_idxs[-(1 + idx)]
            idx += 1
        assert last_right_valid_attr[1] == last_sep_idx
        if idx > 1:
            assert last_right_valid_attr[1] == max_len - 1
            right_trunc = True

        return left_trunc or right_trunc

    assert isinstance(left_entity, pd.Series), "Wrong data type for parameter 'left_entity'."
    assert isinstance(right_entity, pd.Series), "Wrong data type for parameter 'right_entity'."
    assert isinstance(max_len, int), "Wrong data type for parameter 'max_len'."

    sent1 = ""
    sent2 = ""
    left_attr_len_map = []
    for attr, attr_val in left_entity.iteritems():
        sent1 += "{} ".format(str(attr_val))
        left_attr_len_map.append(len(str(attr_val).split()))
    right_attr_len_map = []
    for attr, attr_val in right_entity.iteritems():
        sent2 += "{} ".format(str(attr_val))
        right_attr_len_map.append(len(str(attr_val).split()))
    sent1 = sent1[:-1]
    sent2 = sent2[:-1]

    left_word_idxs, right_word_idxs, tokens = get_sent_pair_word_idxs(sent1, sent2, tokenizer, max_len)

    cum_len = 0
    left_attr_idxs = []
    last_left_attr_idx = None
    left_trunc = False
    for left_attr_len in left_attr_len_map:

        if left_trunc:
            left_attr_idxs.append(None)
        else:

            left_attr_words = left_word_idxs[cum_len: cum_len + left_attr_len]
            assert len(left_attr_words) <= left_attr_len
            if len(left_attr_words) < left_attr_len or len(left_attr_words) == 0:
                left_trunc = True

            if len(left_attr_words) > 0:
                left_attr_start_idx = left_attr_words[0][0]
                left_attr_end_idx = left_attr_words[-1][1]
                left_attr_idxs.append((left_attr_start_idx, left_attr_end_idx))
                last_left_attr_idx = left_attr_end_idx

                cum_len += left_attr_len
            else:
                left_attr_idxs.append(None)

    assert last_left_attr_idx is not None

    cum_len = 0
    right_attr_idxs = []
    right_trunc = False
    for iix, right_attr_len in enumerate(right_attr_len_map):

        if right_trunc:
            right_attr_idxs.append(None)
        else:

            right_attr_words = right_word_idxs[cum_len: cum_len + right_attr_len]
            assert len(right_attr_words) <= right_attr_len
            if len(right_attr_words) < right_attr_len or len(right_attr_words) == 0:
                right_trunc = True

            if len(right_attr_words) > 0:
                right_attr_start_idx = right_attr_words[0][0]
                right_attr_end_idx = right_attr_words[-1][1]
                right_attr_idxs.append((right_attr_start_idx + last_left_attr_idx,
                                        right_attr_end_idx + last_left_attr_idx))

                cum_len += right_attr_len
            else:
                right_attr_idxs.append(None)

    tokens = [t for t in tokens if t != tokenizer.pad_token]

    truncation = _check_attr_idxs_consistency(left_attr_idxs, right_attr_idxs, tokens, len(left_entity), max_len)
    if truncation:
        logging.info("Exceeded max len -> truncated attributes. No attribute data will be returned.")
        return None

    out_data = {
        'left_names': [f'l_{c}' for c in list(left_entity.index)],
        'right_names': [f'r_{c}' for c in list(right_entity.index)],
        'left_idxs': left_attr_idxs,
        'right_idxs': right_attr_idxs
    }

    return out_data


def tokenize_entity_pair(entity1: pd.Series, entity2: pd.Series, tokenizer, tokenize_method: str, max_len: int,
                         return_offset: bool = False, typeMask: str = 'off', columnMask: str = ''):

    assert isinstance(entity1, pd.Series), "Wrong data type for param 'entity1'."
    assert isinstance(entity2, pd.Series), "Wrong data type for param 'entity2'."
    tok_methods = ['sent_pair', 'attr', 'attr_pair']
    assert isinstance(tokenize_method, str), "Wrong data type for param 'tokenize_method'."
    assert tokenize_method in tok_methods, f"tokenize method {tokenize_method} not in {tok_methods}."
    assert isinstance(max_len, int), "Wrong data type for param 'max_len'."

    if tokenize_method == 'sent_pair':

        sent1 = ' '.join([str(val) for val in entity1.to_list()])  # if val != unk_token])
        sent2 = ' '.join([str(val) for val in entity2.to_list()])  # if val != unk_token])


        # Tokenize the text pairs
        features = tokenizer(sent1, sent2, padding='max_length', truncation=True, return_tensors="pt",
                             max_length=max_len, add_special_tokens=True, pad_to_max_length=True,
                             return_attention_mask=True, return_offsets_mapping=return_offset)

        if typeMask == 'random':
            features = mask_random(features)
        if typeMask == 'selectCol':
            print('I cant mask entire sentence')
            exit(0)
        if typeMask == 'maskSyn':
            features = mask_syn(sent1, sent2, features)
        if typeMask == 'maskSem':
            features = mask_sem(sent1, sent2, features)

    elif tokenize_method == 'attr':
        sent = ""
        for attr_val in entity1.to_list():
            sent += "{} [SEP] ".format(str(attr_val))
        for attr_val in entity2.to_list():
            sent += "{} [SEP] ".format(str(attr_val))
        sent = sent[:-7]  # remove last ' [SEP] '
        features = tokenizer(sent, padding='max_length', truncation=True, return_tensors="pt", max_length=max_len,
                             add_special_tokens=True, pad_to_max_length=True, return_attention_mask=True,
                             return_offsets_mapping=return_offset)

        sent1 = sent[:]
        sent2 = None

    elif tokenize_method == 'attr_pair':
        sent1 = ""
        sent2 = ""

        if typeMask == 'selectCol':
            columnMaskInt = list(map(int, re.findall('(\d+)', columnMask)))
            if len(entity1.to_list()) < max(columnMaskInt):
                print('Some of the column provided wont be considered because are higher than the numbers of attributes.')
            sent1, sent2 = mask_column(entity1, entity2, columnMaskInt)
        else:
            for attr_val in entity1.to_list():
                sent1 += "{} [SEP] ".format(str(attr_val))
            sent1 = sent1[:-7]  # remove last ' [SEP] '

            for attr_val in entity2.to_list():
                sent2 += "{} [SEP] ".format(str(attr_val))
            sent2 = sent2[:-7]  # remove last ' [SEP] '

        features = tokenizer(sent1, sent2, padding='max_length', truncation=True, return_tensors="pt",
                             max_length=max_len, add_special_tokens=True, pad_to_max_length=True,
                             return_attention_mask=True, return_offsets_mapping=return_offset)

        if typeMask == 'random':
            features = mask_random(features)
        elif typeMask == 'maskSyn':
            features = mask_syn(sent1, sent2, features, '[SEP]')
    else:
        raise ValueError("Wrong tokenization method.")

    flat_features = {}
    for feature in features:
        flat_features[feature] = features[feature].squeeze(0)
    flat_features['sent1'] = sent1
    flat_features['sent2'] = sent2

    return flat_features

def mask_random(features):
    input_ids = features['input_ids'].unsqueeze(0)
    rand = torch.rand(input_ids.shape)
    mask_arr = (rand < 0.15) * (input_ids != 101) * (input_ids != 102) * (input_ids != 0)
    selection = torch.flatten((mask_arr[0][0]).nonzero()).tolist()
    input_ids[0][0, selection] = 103
    features['inputs_ids'] = input_ids
    return features

def mask_column(entity1, entity2, columnMask):
    sent1 = ""
    attr = 0
    for attr_val in entity1.to_list():
        if attr in columnMask:
            attr_val = '[MASK]'
        sent1 += "{} [SEP] ".format(str(attr_val))
        attr += 1

    sent1 = sent1[:-7]  # remove last ' [SEP] '

    sent2 = ""
    attr = 0
    for attr_val in entity2.to_list():
        if attr in columnMask:
            attr_val = '[MASK]'
        attr += 1
        sent2 += "{} [SEP] ".format(str(attr_val))
    sent2 = sent2[:-7]  # remove last ' [SEP] '
    return sent1, sent2


def mask_syn(sent1, sent2, features, sep: str = ' '):

    top_word_pairs_by_syntax = nlp.get_syntactically_similar_words_from_sent_pair \
        (sent1.split(sep), sent2.split(sep), 3, "edit", return_idxs=True, return_sims=True)

    input_ids = features['input_ids'].unsqueeze(0)
    for couple in top_word_pairs_by_syntax['word_pair_idxs']:
        if sep == ' ':
            index_mask = get_index_token_sent(couple, features.word_ids())
        else:
            index_mask = get_index_token_attr(couple, features.tokens(), features.word_ids())
        for val_mask in index_mask:
            input_ids[0][0, val_mask] = 103

    features['inputs_ids'] = input_ids
    return features


def mask_sem(sent1, sent2, features, sep: str= ' '):

    if os.path.isfile('modelPick.pkl'):
        sem_emb_model = pickle.load(open( "modelPick.pkl", "rb"))
    else:
        FAST_TEXT_PATH = os.path.join('C:\\Users\\jeson\\PycharmProjects\\bert-attention-for-em\\data', 'wiki-news-300d-1M', 'wiki-news-300d-1M.vec')
        sem_emb_model = gensim.models.KeyedVectors.load_word2vec_format(FAST_TEXT_PATH, binary=False, encoding='utf8')
        pickle.dump(sem_emb_model, open("modelPick.pkl", "wb"))

    top_word_pairs_by_semantic = nlp.get_semantically_similar_words_from_sent_pair\
        (sent1.split(sep), sent2.split(sep), sem_emb_model, 0.1, return_idxs=True, return_sims=True)

    input_ids = features['input_ids'].unsqueeze(0)
    for couple in top_word_pairs_by_semantic['word_pair_idxs']:
        if sep == ' ':
            index_mask = get_index_token_sent(couple, features.word_ids())
        else:
            index_mask = get_index_token_attr(couple, features.tokens(), features.word_ids())
        for val_mask in index_mask:
            input_ids[0][0, val_mask] = 103

    features['inputs_ids'] = input_ids
    return features


def get_index_token_sent(couple, list_idx_word):

    idx_first = [i for i, j in enumerate(list_idx_word) if j == couple[0]]
    idx_second = [i for i, j in enumerate(list_idx_word) if j == couple[1]]
    idx_second_none = [i for i, j in enumerate(list_idx_word) if j is None][1]
    listMask = [j for j in idx_first if j < idx_second_none] + [j for j in idx_second if j > idx_second_none]
    return listMask


def get_index_token_attr(couple, list_token, list_idx_word):

    listTokenMask = []
    indexSep = [0, [i for i, j in enumerate(list_idx_word) if j is None][1], [i for i, j in enumerate(list_idx_word) if j is None][2]]
    for i in range(len(indexSep)-1):
        idxCouple = 0
        countSep = 0
        for wordIdx in range(indexSep[i]+1, indexSep[i+1]):
            if list_token[wordIdx] == '[SEP]':
                countSep += 1
            if countSep == couple[idxCouple]:
                listTokenMask.append(wordIdx)
            if countSep > couple[idxCouple]:
                idxCouple += 1
                break
    return listTokenMask


