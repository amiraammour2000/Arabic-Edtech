# generators/vocab_extract.py
"""Générateur d'extraction de vocabulaire."""
import random
import uuid
from typing import List
from loguru import logger
from core.nlp_pipeline import NLPPipeline, Sentence
from core.models import VocabWord
from core import linguistics_db as db


class VocabExtractGenerator:
    def __init__(self, nlp: NLPPipeline):
        self.nlp = nlp

    def generate(self, sentences: List[Sentence], num_words: int = 5) -> List[VocabWord]:
        # Collecter tous les tokens candidats
        candidates = []
        for sent in sentences:
            for tok in sent.tokens:
                if (tok.bare not in db.STOP_WORDS
                        and len(tok.bare) > 4
                        and tok.pos in ("noun", "verb", "adj", "N", "V", "ADJ")
                        and not tok.bare.startswith("ال")):
                    candidates.append((sent, tok))

        if not candidates:
            return []

        selected = random.sample(candidates, min(num_words, len(candidates)))
        words = []
        for sent, tok in selected:
            # Trouver des synonymes dans le même champ sémantique
            field = None
            for f, ws in db.SEMANTIC_FIELDS.items():
                if tok.bare in ws:
                    field = f
                    break

            synonyms = []
            if field:
                pool = [w for w in db.SEMANTIC_FIELDS[field] if w != tok.bare]
                synonyms = random.sample(pool, min(2, len(pool)))

            words.append(VocabWord(
                word=tok.bare,
                vocalized=tok.text,
                root=tok.root,
                pos=tok.pos,
                context_sentence=sent.text,
                synonyms=synonyms,
                points=1,
            ))

        logger.info("Extracted {} vocabulary words.", len(words))
        return words