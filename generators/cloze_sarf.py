# generators/cloze_sarf.py
"""Générateur de trous morphologiques (صرف) — dérivation."""
import random
import uuid
from typing import List
from loguru import logger
from core.nlp_pipeline import NLPPipeline, Sentence, Token
from core.models import QuestionCloze, DifficultyLevel, BloomLevel
from core import linguistics_db as db


class ClozeSarfGenerator:
    def __init__(self, nlp: NLPPipeline):
        self.nlp = nlp

    def generate(self, sentences: List[Sentence], num_questions: int = 3,
                 difficulty: str = "B1") -> List[QuestionCloze]:
        # Cibler les mots dérivables (noms d'action, ism fa3il, etc.)
        targets = []
        for sent in sentences:
            for tok in sent.tokens:
                if self._is_sarf_target(tok):
                    targets.append((sent, tok))

        if not targets:
            logger.warning("No sarf targets found.")
            return []

        selected = random.sample(targets, min(num_questions, len(targets)))
        questions = []
        for sent, tok in selected:
            q = self._build_question(sent, tok, difficulty)
            if q:
                questions.append(q)

        logger.info("Generated {} sarf cloze questions.", len(questions))
        return questions

    def _is_sarf_target(self, tok: Token) -> bool:
        """Vérifie si un token est une bonne cible pour un exercice de sarf."""
        bare = tok.bare
        if len(bare) < 4 or bare in db.STOP_WORDS:
            return False

        # Cibler: مُفْعِل، مُفْعَل، مُسْتَفْعِل، فاعل، مفعول
        prefixes = ["مُ", "مَ", "مُسْت", "مُت"]
        for p in prefixes:
            if bare.startswith(p.replace("ْ", "")):
                return True

        # Cibler les patterns connus
        if tok.pattern and tok.pattern in db.SARF_PATTERNS:
            return True

        return False

    def _build_question(self, sent: Sentence, tok: Token, difficulty: str) -> QuestionCloze:
        # Identifier le pattern
        pattern = tok.pattern or "فَعَلَ"
        pattern_info = db.SARF_PATTERNS.get(pattern, db.SARF_PATTERNS["فَعَلَ"])

        # Construire la question
        cloze_sent = sent.text.replace(tok.text, "............", 1)

        # I3rab pour le sarf
        root = tok.root or "—"
        i3rab_text = (
            f"الكلمة: {tok.text} | الوزن: {pattern} | الجذر: {root} | "
            f"نوعه: {pattern_info.get('type', '—')} | "
            f"اسم الفاعل: {pattern_info.get('ism_faail', '—')} | "
            f"اسم المفعول: {pattern_info.get('ism_maf3ul', '—')} | "
            f"المصدر: {pattern_info.get('masdar', '—')}"
        )

        return QuestionCloze(
            id=str(uuid.uuid4())[:8],
            original_sentence=sent.text,
            cloze_sentence=cloze_sent,
            answer=tok.bare,
            answer_vocalized=tok.text,
            i3rab_rule=f"اشتقاق صرفي — وزن «{pattern}»",
            i3rab_detailed=i3rab_text,
            grammar_category="sarf",
            points=2,
            bloom_level=BloomLevel.ANALYZE,
            difficulty=DifficultyLevel(difficulty.split(" ")[0]) if " " in difficulty else DifficultyLevel.B1,
        )