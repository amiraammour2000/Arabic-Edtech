# core/distractor_engine.py
"""
Génération de distracteurs pédagogiquement fondés pour les QCM.
Stratégies:
  1. Même racine (جذر), schème différent → confusion morphologique
  2. Même champ sémantique → confusion lexicale
  3. Même schème, racine différente → confusion formelle
  4. Fréquence calibrée → difficulté adaptée
"""
import random
from typing import List, Optional, Set, Tuple
from loguru import logger
from core.nlp_pipeline import NLPPipeline, Token
from core import linguistics_db as db
import pyarabic.araby as araby


class DistractorEngine:

    def __init__(self, nlp: NLPPipeline):
        self.nlp = nlp
        self._semantic_index = self._build_semantic_index()

    def _build_semantic_index(self) -> dict:
        """Indexe tous les mots par champ sémantique."""
        index = {}
        for field, words in db.SEMANTIC_FIELDS.items():
            for w in words:
                index[w] = field
        return index

    def generate_distractors(
        self,
        target_word: str,
        target_pos: str = None,
        target_root: str = None,
        count: int = 3,
        difficulty: str = "B1"
    ) -> List[str]:
        """
        Génère `count` distracteurs pour `target_word`.
        Orchestre plusieurs stratégies et valide le résultat.
        """
        candidates: Set[str] = set()

        # Stratégie 1: Même racine, schème différent
        if target_root and len(target_root) == 3:
            root_distractors = self._root_based_distractors(target_word, target_root)
            candidates.update(root_distractors)

        # Stratégie 2: Même champ sémantique
        field = self._semantic_index.get(araby.strip_tashkeel(target_word))
        if field:
            field_distractors = self._semantic_field_distractors(target_word, field)
            candidates.update(field_distractors)

        # Stratégie 3: Même POS, fréquence similaire
        pos_distractors = self._pos_frequency_distractors(target_word, target_pos, difficulty)
        candidates.update(pos_distractors)

        # Stratégie 4: Distracteurs par schème (si pattern connu)
        pattern = self.nlp.get_pattern(target_word)
        if pattern:
            pattern_distractors = self._pattern_based_distractors(target_word, pattern)
            candidates.update(pattern_distractors)

        # Stratégie 5: Fallback — pioche dans le champ sémantique le plus proche
        if len(candidates) < count:
            fallback = self._fallback_distractors(target_word, count - len(candidates))
            candidates.update(fallback)

        # Nettoyage: supprimer le mot cible et les doublons
        bare_target = araby.strip_tashkeel(target_word)
        candidates = {d for d in candidates if araby.strip_tashkeel(d) != bare_target and len(d) > 2}

        # Sélection finale avec calibrage de difficulté
        final = self._select_by_difficulty(list(candidates), difficulty, count)

        # Si on n'a toujours pas assez, compléter aléatoirement
        while len(final) < count:
            pool = [w for words in db.SEMANTIC_FIELDS.values() for w in words]
            extra = random.choice(pool)
            if extra not in final and extra != bare_target:
                final.append(extra)

        logger.debug("Distractors for '{}': {}", target_word, final[:count])
        return final[:count]

    def _root_based_distractors(self, word: str, root: str) -> List[str]:
        """Génère des mots de même racine mais de schème différent."""
        # Bibliothèque de transformations par racine
        # Exemple: كتب → كاتب، مكتوب، كتاب، مكتب، كتب، كتّاب
        transformations = {
            "فعل": [root[0] + "َ" + root[1] + "َ" + root[2] + "َ"],  # فَعَلَ
            "فاعل": [root[0] + "َا" + root[1] + root[2]],  # فاعل
            "مفعول": ["م" + root[0] + root[1] + "و" + root[2]],  # مفعول
            "فعيل": [root[0] + "َ" + root[1] + "ي" + root[2]],  # فعيل
            "فعّال": [root[0] + "َ" + root[1] + root[1] + "ا" + root[2]],  # فعّال
            "مفعِل": ["م" + root[0] + "ْ" + root[1] + "ِ" + root[2]],  # مفعِل
            "استفعال": ["ا" + root[0] + "ْت" + root[1] + "َا" + root[2]],  # استفعال
        }

        result = []
        for pattern, generated in transformations.items():
            for g in generated:
                # Valider que ce n'est pas le mot original
                if araby.strip_tashkeel(g) != araby.strip_tashkeel(word):
                    result.append(g)

        return result

    def _semantic_field_distractors(self, word: str, field: str) -> List[str]:
        """Renvoie des mots du même champ sémantique."""
        words = db.SEMANTIC_FIELDS.get(field, [])
        bare = araby.strip_tashkeel(word)
        return [w for w in words if araby.strip_tashkeel(w) != bare]

    def _pos_frequency_distractors(self, word: str, pos: str, difficulty: str) -> List[str]:
        """Sélectionne des distracteurs basés sur la fréquence et le POS."""
        if difficulty in ("A1", "A2"):
            pool = list(db.HIGH_FREQ_WORDS)
        elif difficulty in ("B1", "B2"):
            pool = list(db.HIGH_FREQ_WORDS) + list(db.MID_FREQ_WORDS)
        else:
            pool = list(db.MID_FREQ_WORDS) + list(db.LOW_FREQ_WORDS)

        bare = araby.strip_tashkeel(word)
        return [w for w in pool if w != bare]

    def _pattern_based_distractors(self, word: str, pattern: str) -> List[str]:
        """Génère des mots avec le même schème morphologique."""
        # Extraction de la racine à partir du pattern
        root = self.nlp.get_root(word)
        if not root or len(root) != 3:
            return []

        # Appliquer le même pattern à des racines différentes courantes
        sample_roots = ["كتب", "قرأ", "علم", "فهم", "عمل", "درس", "فتح", "نصر"]
        result = []
        for r in sample_roots:
            if r == root:
                continue
            generated = self._apply_pattern(r, pattern)
            if generated and generated != araby.strip_tashkeel(word):
                result.append(generated)

        return result

    def _apply_pattern(self, root: str, pattern: str) -> Optional[str]:
        """Applique un schème à une racine trilitère."""
        if len(root) != 3 or not pattern:
            return None
        # Substitution simple ف→root[0], ع→root[1], ل→root[2]
        mapping = {"ف": root[0], "ع": root[1], "ل": root[2]}
        result = ""
        for ch in pattern:
            if ch in mapping:
                result += mapping[ch]
            else:
                result += ch
        return result

    def _fallback_distractors(self, word: str, count: int) -> List[str]:
        """Dernier recours: mots aléatoires de fréquence similaire."""
        all_words = [w for words in db.SEMANTIC_FIELDS.values() for w in words]
        bare = araby.strip_tashkeel(word)
        pool = [w for w in all_words if w != bare]
        return random.sample(pool, min(count, len(pool)))

    def _select_by_difficulty(self, candidates: List[str], difficulty: str, count: int) -> List[str]:
        """Calibre la difficulté des distracteurs."""
        if not candidates:
            return []

        # Pour A1-A2: préférer les mots fréquents
        # Pour C1-C2: préférer les mots rares
        if difficulty in ("A1", "A2"):
            preferred = [c for c in candidates if c in db.HIGH_FREQ_WORDS]
            others = [c for c in candidates if c not in db.HIGH_FREQ_WORDS]
        elif difficulty in ("B1", "B2"):
            preferred = [c for c in candidates if c in db.MID_FREQ_WORDS or c in db.HIGH_FREQ_WORDS]
            others = [c for c in candidates if c not in preferred]
        else:
            preferred = [c for c in candidates if c in db.LOW_FREQ_WORDS or c in db.MID_FREQ_WORDS]
            others = [c for c in candidates if c not in preferred]

        random.shuffle(preferred)
        random.shuffle(others)

        result = (preferred + others)[:count]
        return result