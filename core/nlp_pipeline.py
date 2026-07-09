# core/nlp_pipeline.py
"""
Pipeline NLP arabe multi-couches avec fallbacks.
Utilise CAMeL Tools comme moteur principal (gold standard académique).
"""
import re
import functools
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import pyarabic.araby as araby

# Tentative d'import CAMeL Tools (avec fallback gracieux)
try:
    from camel_tools.tokenizers.word import simple_word_tokenize
    from camel_tools.pos import MLEPOSLabeler
    from camel_tools.ner import NERecognizer
    from camel_tools.morphology.database import MorphologyDB
    from camel_tools.morphology.analyzer import Analyzer
    from camel_tools.diacritization.diacritizer import Diacritizer
    CAMEL_AVAILABLE = True
    logger.info("CAMeL Tools loaded — full NLP pipeline active.")
except ImportError:
    CAMEL_AVAILABLE = False
    logger.warning("CAMeL Tools unavailable — using fallback pipeline.")

# Fallback: Mishkal pour diacritization
try:
    from mishkal.tashkeel import TashkeelClass
    MISHKAL_AVAILABLE = True
except ImportError:
    MISHKAL_AVAILABLE = False


@dataclass
class Token:
    text: str                    # Mot avec diacritiques
    bare: str                    # Mot sans diacritiques
    lemma: str                   # Lemme
    pos: str                     # Part-of-speech
    pos_fine: str                # POS granulaire
    root: Optional[str]          # Racine (جذر)
    pattern: Optional[str]       # Schème (وزن)
    ner: Optional[str]           # Named entity
    index: int                   # Position dans la phrase
    sentence_index: int


@dataclass
class Sentence:
    text: str                    # Phrase complète vocalisée
    raw: str                     # Phrase sans diacritiques
    tokens: List[Token]
    index: int


class NLPPipeline:
    """Pipeline NLP unifié avec dégradation gracieuse."""

    _instance: Optional["NLPPipeline"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._init_camel()
        self._init_mishkal()
        self._initialized = True
        logger.info("NLPPipeline ready (CAMeL={}, Mishkal={})",
                     CAMEL_AVAILABLE, MISHKAL_AVAILABLE)

    def _init_camel(self):
        """Initialise les composants CAMeL Tools."""
        self._camel_pos = None
        self._camel_ner = None
        self._camel_analyzer = None
        self._camel_diac = None

        if not CAMEL_AVAILABLE:
            return

        try:
            db = MorphologyDB.built_db()
            self._camel_analyzer = Analyzer(db)
            self._camel_pos = MLEPOSLabeler.pretrained()
            self._camel_ner = NERecognizer.pretrained()
            self._camel_diac = Diacritizer.pretrained()
        except Exception as e:
            logger.error("CAMeL init failed: {}", e)

    def _init_mishkal(self):
        if MISHKAL_AVAILABLE:
            self._mishkal = TashkeelClass()
        else:
            self._mishkal = None

    # ===================== PRÉTRAITEMENT =====================

    def preprocess(self, text: str) -> str:
        """Nettoyage agressif avant NLP."""
        # Normalisation Unicode
        text = araby.normalize_ligature(text)
        text = araby.normalize_teh(text)
        # Retours à ligne → espaces
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        # Espaces multiples → un seul
        text = re.sub(r'\s+', ' ', text).strip()
        # Espace après ponctuation arabe
        text = re.sub(r'([؟!،.:؛])([^\s])', r'\1 \2', text)
        # Supprimer le tatweel
        text = araby.strip_tatweel(text)
        return text

    # ===================== VOCALISATION =====================

    def diacritize(self, text: str) -> str:
        """Vocalisation multi-stratégie avec fallback."""
        clean = self.preprocess(text)

        # Stratégie 1: CAMeL Tools (meilleure précision)
        if self._camel_diac is not None:
            try:
                result = self._camel_diac.diacritize(clean)
                if result and araby.is_arabicstring(result):
                    return self._postprocess_diacritics(result)
            except Exception as e:
                logger.warning("CAMeL diacritization failed: {}", e)

        # Stratégie 2: Mishkal (fallback solide)
        if self._mishkal is not None:
            try:
                result = self._mishkal.tashkeel(clean)
                if result:
                    return self._postprocess_diacritics(result)
            except Exception as e:
                logger.warning("Mishkal diacritization failed: {}", e)

        # Stratégie 3: Pas de vocalisation (dégradé)
        logger.error("All diacritization methods failed.")
        return clean

    def _postprocess_diacritics(self, text: str) -> str:
        """Nettoyage post-vocalisation."""
        text = araby.strip_tatweel(text)
        text = re.sub(r'([؟!،.:؛])([^\s])', r'\1 \2', text)
        # Supprimer les diacritiques doubles (bug de certains modèles)
        text = re.sub(r'[\u064B-\u0652]{2,}', '', text)
        return text

    # ===================== TOKENISATION =====================

    def tokenize(self, text: str) -> List[str]:
        """Tokenisation optimale."""
        if CAMEL_AVAILABLE:
            try:
                return simple_word_tokenize(text)
            except Exception:
                pass
        return araby.tokenize(text)

    # ===================== ANALYSE MORPHOLOGIQUE =====================

    def analyze_word(self, word: str) -> Dict:
        """Analyse morphologique complète d'un mot."""
        bare = araby.strip_tashkeel(word)

        result = {
            "word": word,
            "bare": bare,
            "lemma": bare,
            "pos": "UNK",
            "pos_fine": "UNK",
            "root": None,
            "pattern": None,
        }

        if self._camel_analyzer is not None:
            try:
                analyses = self._camel_analyzer.analyze(bare)
                if analyses:
                    best = analyses[0]
                    result["lemma"] = best.get("lex", bare)
                    result["pos"] = best.get("pos", "UNK")
                    result["pos_fine"] = best.get("pos", "UNK")
                    root = best.get("root")
                    if root and len(root) == 3:
                        result["root"] = root
                    pattern = best.get("pattern")
                    if pattern:
                        result["pattern"] = pattern
            except Exception as e:
                logger.debug("Analysis failed for '{}': {}", bare, e)

        return result

    # ===================== POS TAGGING =====================

    def pos_tag(self, tokens: List[str]) -> List[str]:
        """Étiquetage morphosyntaxique."""
        if self._camel_pos is not None:
            try:
                return self._camel_pos.predict(tokens)
            except Exception:
                pass
        # Fallback: heuristiques simples
        return [self._heuristic_pos(t) for t in tokens]

    def _heuristic_pos(self, token: str) -> str:
        """POS heuristique de secours."""
        bare = araby.strip_tashkeel(token)
        if bare in ["في", "من", "إلى", "على", "عن", "مع", "ب", "ل", "ك"]:
            return "prep"
        if bare in ["هو", "هي", "هم", "هن", "أنا", "نحن", "أنت", "أنتم"]:
            return "pron"
        if bare.startswith("ال"):
            return "noun"
        if bare.endswith("ة"):
            return "noun"
        return "noun"

    # ===================== NER =====================

    def named_entities(self, tokens: List[str]) -> List[str]:
        if self._camel_ner is not None:
            try:
                return self._camel_ner.predict(tokens)
            except Exception:
                pass
        return ["O"] * len(tokens)

    # ===================== PIPELINE COMPLET =====================

    def process(self, text: str) -> List[Sentence]:
        """Pipeline complet: tokenize → POS → NER → morpho."""
        clean = self.preprocess(text)
        vocalized = self.diacritize(clean)

        # Découpage en phrases
        raw_sentences = re.split(r'([.؟!])\s*', vocalized)
        merged = []
        for i in range(0, len(raw_sentences) - 1, 2):
            merged.append(raw_sentences[i] + (raw_sentences[i + 1] if i + 1 < len(raw_sentences) else ""))
        if raw_sentences and len(raw_sentences) % 2 == 1:
            merged.append(raw_sentences[-1])

        sentences = []
        for s_idx, sent_text in enumerate(merged):
            sent_text = sent_text.strip()
            if not sent_text or len(sent_text.split()) < 3:
                continue

            tokens_str = self.tokenize(sent_text)
            pos_tags = self.pos_tag(tokens_str)
            ner_tags = self.named_entities(tokens_str)

            tokens = []
            for t_idx, (tok, pos, ner) in enumerate(zip(tokens_str, pos_tags, ner_tags)):
                analysis = self.analyze_word(tok)
                tokens.append(Token(
                    text=tok,
                    bare=analysis["bare"],
                    lemma=analysis["lemma"],
                    pos=pos,
                    pos_fine=analysis["pos_fine"],
                    root=analysis["root"],
                    pattern=analysis["pattern"],
                    ner=ner if ner != "O" else None,
                    index=t_idx,
                    sentence_index=s_idx,
                ))

            sentences.append(Sentence(
                text=sent_text,
                raw=araby.strip_tashkeel(sent_text),
                tokens=tokens,
                index=s_idx,
            ))

        logger.info("NLP pipeline: {} sentences, {} tokens processed.",
                     len(sentences), sum(len(s.tokens) for s in sentences))
        return sentences

    # ===================== UTILITAIRES =====================

    def get_root(self, word: str) -> Optional[str]:
        """Extrait la racine trilitère d'un mot."""
        analysis = self.analyze_word(word)
        return analysis.get("root")

    def get_pattern(self, word: str) -> Optional[str]:
        """Extrait le schème morphologique."""
        analysis = self.analyze_word(word)
        return analysis.get("pattern")