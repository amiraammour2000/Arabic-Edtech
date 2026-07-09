# core/i3rab_engine.py
"""
Moteur d'analyse syntaxique arabe (إعراب) basé sur les règles du Nahw.
Utilise les POS tags du pipeline NLP pour produire des énoncés d'i3rab précis.
"""
import re
from typing import Optional, Tuple, List
from loguru import logger
from core.nlp_pipeline import NLPPipeline, Token, Sentence
from core import linguistics_db as db


class I3rabEngine:
    """Génère l'analyse grammaticale (إعراب) d'un mot dans son contexte."""

    def __init__(self, nlp: NLPPipeline):
        self.nlp = nlp

    def analyze_token(self, sentence: Sentence, token: Token) -> str:
        """
        Produit l'i3rab complet d'un token dans sa phrase.
        Retourne une chaîne arabe descriptive.
        """
        tokens = sentence.tokens
        idx = token.index

        # 1. Vérifier les règles des nawasikh (إنّ / كان)
        i3rab = self._check_nawasikh(tokens, idx)
        if i3rab:
            return i3rab

        # 2. Vérifier les حروف الجر
        i3rab = self._check_preposition(tokens, idx)
        if i3rab:
            return i3rab

        # 3. Vérifier المفعول به
        i3rab = self._check_maf3ul_bihi(tokens, idx)
        if i3rab:
            return i3rab

        # 4. Vérifier المبتدأ والخبر
        i3rab = self._check_mubtada_khabar(tokens, idx)
        if i3rab:
            return i3rab

        # 5. Vérifier النعت (صفة)
        i3rab = self._check_naat(tokens, idx)
        if i3rab:
            return i3rab

        # 6. Défaut: analyse POS basique
        return self._default_i3rab(token)

    def _check_nawasikh(self, tokens: List[Token], idx: int) -> Optional[str]:
        """Détecte إنّ وأخواتها / كان وأخواتها et analyse le mot suivant."""
        if idx == 0 or idx >= len(tokens):
            return None

        prev = tokens[idx - 1]
        prev_bare = prev.bare

        # إنّ وأخواتها
        for word, info in db.NAHW_RULES["inna_family"]["items"].items():
            bare_word = re.sub(r'[ًٌٌٍٍَُِّْ]', '', word)
            if prev_bare == bare_word:
                # FIX: Ignorer "أنْ" المصدرية si le mot suivant est un verbe
                if bare_word in ["أن", "إن"] and tokens[idx].pos in ("verb", "V"):
                    continue
                template = db.NAHW_RULES["inna_family"]["i3rab_template"]
                # Trouver le khabar (2 mots après)
                khabar = tokens[idx + 1].bare if idx + 1 < len(tokens) else "..."
                return template.format(
                    word=word,
                    subject=tokens[idx].bare,
                    khabar=khabar
                )

        # كان وأخواتها
        for word, info in db.NAHW_RULES["kana_family"]["items"].items():
            bare_word = re.sub(r'[ًٌٌٍٍَُِّْ]', '', word)
            if prev_bare == bare_word:
                template = db.NAHW_RULES["kana_family"]["i3rab_template"]
                khabar = tokens[idx + 1].bare if idx + 1 < len(tokens) else "..."
                return template.format(
                    word=word,
                    subject=tokens[idx].bare,
                    khabar=khabar
                )

        return None

    def _check_preposition(self, tokens: List[Token], idx: int) -> Optional[str]:
        """Détecte حرف الجر + اسم مجرور."""
        if idx == 0:
            return None

        prev = tokens[idx - 1]
        bare_prev = prev.bare

        for prep, info in db.NAHW_RULES["huruf_jarr"]["items"].items():
            prep_clean = prep.replace("ـ", "").replace("ْ", "")
            if bare_prev == prep_clean or bare_prev == prep:
                template = db.NAHW_RULES["huruf_jarr"]["i3rab_template"]
                return template.format(word=prep, object=tokens[idx].bare)

        return None

    def _check_maf3ul_bihi(self, tokens: List[Token], idx: int) -> Optional[str]:
        """Détecte المفعول به après un verbe transitif."""
        if idx == 0:
            return None

        prev = tokens[idx - 1]
        # Si le précédent est un verbe et le courant est un nom
        if prev.pos in ("verb", "V") and tokens[idx].pos in ("noun", "N", "adj"):
            # Vérifier que ce n'est pas un حرف الجر avant
            if idx >= 2 and tokens[idx - 2].bare in db.NAHW_RULES["huruf_jarr"]["items"]:
                return None
            # Vérifier que le verbe est transitif
            if prev.bare in db.NAHW_RULES["maf3ul_bihi"]["triggers"]:
                template = db.NAHW_RULES["maf3ul_bihi"]["i3rab_template"]
                return template.format(word=tokens[idx].bare)

        return None

    def _check_mubtada_khabar(self, tokens: List[Token], idx: int) -> Optional[str]:
        """Détecte المبتدأ والخبر dans une جملة اسمية."""
        # Si c'est le premier token de la phrase et c'est un nom
        if idx == 0 and tokens[idx].pos in ("noun", "N"):
            # Le khabar est généralement le 2e ou 3e nom
            khabar_idx = None
            for j in range(1, min(4, len(tokens))):
                if tokens[j].pos in ("noun", "N", "adj", "ADJ") and tokens[j].bare not in db.STOP_WORDS:
                    khabar_idx = j
                    break
            if khabar_idx:
                template = db.NAHW_RULES["mubtada_khabar"]["i3rab_template"]
                return template.format(
                    subject=tokens[idx].bare,
                    khabar=tokens[khabar_idx].bare
                )
        return None

    def _check_naat(self, tokens: List[Token], idx: int) -> Optional[str]:
        """Détecte النعت (adjectif qui suit un nom)."""
        if idx == 0:
            return None

        prev = tokens[idx - 1]
        # Si le précédent est un nom défini et le courant est un adjectif
        if (prev.pos in ("noun", "N") and
                tokens[idx].pos in ("adj", "ADJ") and
                prev.bare.startswith("ال")):
            # Déterminer le cas
            case = "مرفوع"  # Simplifié: la plupart du temps مرفوع
            template = db.NAHW_RULES["naat"]["i3rab_template"]
            return template.format(word=tokens[idx].bare, case=case)

        return None

    def _default_i3rab(self, token: Token) -> str:
        """I3rab par défaut basé sur le POS."""
        pos_map = {
            "noun": "اسم",
            "verb": "فعل",
            "adj": "صفة",
            "adv": "ظرف",
            "prep": "حرف جر",
            "pron": "ضمير",
            "conj": "حرف عطف",
        }
        pos_ar = pos_map.get(token.pos, "كلمة")
        return f"{token.bare}: {pos_ar}"

    def find_grammar_targets(self, sentences: List[Sentence]) -> List[Tuple[Sentence, Token, str]]:
        """
        Trouve tous les tokens intéressants pour un exercice de grammaire.
        Retourne (phrase, token, type_de_règle).
        """
        targets = []
        for sent in sentences:
            tokens = sent.tokens
            for i, tok in enumerate(tokens):
                if tok.bare in db.STOP_WORDS or len(tok.bare) < 3:
                    continue

                rule_type = self._identify_rule_type(tokens, i)
                if rule_type:
                    targets.append((sent, tok, rule_type))

        logger.info("I3rab engine: {} grammar targets identified.", len(targets))
        return targets

    def _identify_rule_type(self, tokens: List[Token], idx: int) -> Optional[str]:
        """Identifie le type de règle grammaticale applicable."""
        if idx == 0:
            return None

        prev = tokens[idx - 1].bare

        # إنّ وأخواتها
        for word in db.NAHW_RULES["inna_family"]["items"]:
            clean = re.sub(r'[ًٌٌٍٍَُِّْ]', '', word)
            if prev == clean:
                return "inna_family"

        # كان وأخواتها
        for word in db.NAHW_RULES["kana_family"]["items"]:
            clean = re.sub(r'[ًٌٌٍٍَُِّْ]', '', word)
            if prev == clean:
                return "kana_family"

        # حروف الجر
        for prep in db.NAHW_RULES["huruf_jarr"]["items"]:
            if prev == prep.replace("ـ", "").replace("ْ", ""):
                return "huruf_jarr"

        # المفعول به
        if (tokens[idx - 1].pos in ("verb", "V") and
                tokens[idx].pos in ("noun", "N") and
                tokens[idx - 1].bare in db.NAHW_RULES["maf3ul_bihi"]["triggers"]):
            return "maf3ul_bihi"

        return None
