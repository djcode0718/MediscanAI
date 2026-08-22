# import re
# import os
# from symspellpy import SymSpell, Verbosity

# def _load_spell_checker():
#     """Helper function to load the SymSpell object and dictionary only once."""
#     sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
    
#     dictionary_path = os.path.join(os.path.dirname(__file__), "frequency_dictionary_en_82_765.txt")
    
#     if not os.path.exists(dictionary_path):
#         raise FileNotFoundError(f"Dictionary file not found at {dictionary_path}. Please download and place it in the 'backend' folder.")
        
#     sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)
#     return sym_spell

# spell_checker = _load_spell_checker()

# def normalize_text(s: str) -> str:
#     """
#     Cleans and normalizes text using a controlled, word-by-word correction strategy.
#     """
#     if not s:
#         return ""
    
#     placeholders = []
    
#     def replacer(match):
#         placeholders.append(match.group(0))
#         return f" __placeholder_{len(placeholders)-1}__ "
    
#     text_with_placeholders = re.sub(r'(\d+\.?\d*)', replacer, s)

#     text_with_placeholders = text_with_placeholders.strip().lower()
#     text_with_placeholders = re.sub(r'[^\w\s\._-]', ' ', text_with_placeholders)
#     text_with_placeholders = re.sub(r'\s+', ' ', text_with_placeholders)

#     words = text_with_placeholders.split(' ')
#     corrected_words = []
#     for word in words:
#         if not word:
#             continue
#         if word.startswith('__placeholder_'):
#             corrected_words.append(word)
#             continue
        
#         suggestions = spell_checker.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
#         if suggestions:
#             corrected_words.append(suggestions[0].term)
#         else:
#             corrected_words.append(word)

#     corrected_text = ' '.join(corrected_words)
    
#     restored_text = corrected_text
#     for i, num_val in enumerate(placeholders):
#         restored_text = restored_text.replace(f"__placeholder_{i}__", num_val.strip(), 1)
        
#     restored_text = re.sub(r'\s+', ' ', restored_text).strip()
    
#     return restored_text


# backend/utils.py

import json
import re
import os
from typing import Dict
from symspellpy import SymSpell, Verbosity

def load_jsonl_to_dict(path: str, id_key: str = None) -> Dict[str, Dict]:
    """
    Load jsonl file and return mapping id -> record.
    If id_key is provided, uses record[id_key] as key (stringified).
    Otherwise keys are line indices prefixed with "line_{i}".
    """
    m = {}
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:
                raise
            if id_key and id_key in r:
                key = str(r[id_key])
            else:
                if 'id' in r:
                    key = str(r['id'])
                else:
                    key = f"line_{i}"
            m[key] = r
    return m

def _load_spell_checker():
    """Helper function to load the SymSpell object and dictionary only once."""
    sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
    
    dictionary_path = os.path.join(os.path.dirname(__file__), "frequency_dictionary_en_82_765.txt")
    
    if not os.path.exists(dictionary_path):
        raise FileNotFoundError(f"Dictionary file not found at {dictionary_path}. Please download and place it in the 'backend' folder.")
        
    sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)
    return sym_spell

spell_checker = _load_spell_checker()

def normalize_text(s: str) -> str:
    """
    Cleans and normalizes text using a controlled, word-by-word correction strategy.
    """
    if not s:
        return ""
    
    placeholders = []
    
    def replacer(match):
        placeholders.append(match.group(0))
        return f" __placeholder_{len(placeholders)-1}__ "
    
    text_with_placeholders = re.sub(r'(\d+\.?\d*)', replacer, s)

    text_with_placeholders = text_with_placeholders.strip().lower()
    text_with_placeholders = re.sub(r'[^\w\s\._-]', ' ', text_with_placeholders)
    text_with_placeholders = re.sub(r'\s+', ' ', text_with_placeholders)

    words = text_with_placeholders.split(' ')
    corrected_words = []
    for word in words:
        if not word:
            continue
        if word.startswith('__placeholder_'):
            corrected_words.append(word)
            continue
        
        suggestions = spell_checker.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
        if suggestions:
            corrected_words.append(suggestions[0].term)
        else:
            corrected_words.append(word)

    corrected_text = ' '.join(corrected_words)
    
    restored_text = corrected_text
    for i, num_val in enumerate(placeholders):
        restored_text = restored_text.replace(f"__placeholder_{i}__", num_val.strip(), 1)
        
    restored_text = re.sub(r'\s+', ' ', restored_text).strip()
    
    return restored_text