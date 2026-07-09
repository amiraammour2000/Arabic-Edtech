# generators/cloze_nahw.py
"""Générateur de trous grammaticaux (نحو) avec i3rab précis."""
import random
import uuid
from typing import List
from loguru import logger
from core.nlp_pipeline import NLPPipeline, Sentence
from core.models import QuestionCloze, DifficultyLevel, BloomLevel
from core.i3rab_engine import I3rabEngine
from core import linguistics_db as db


class ClozeNahwGenerator:
    def __init__(self, nlp: NLPPipeline, i3rab_engine: I3rabEngine):
        self.nlp = nlp
        self.i3rab = i3rab_engine

    def generate(self, sentences: List[Sentence], num_questions: int = 5,
                 difficulty: str = "B1") -> List[QuestionCloze]:
        # Trouver les cibles grammaticales
        targets = self.i3rab.find_grammar_targets(sentences)

        if not targets:
            logger.warning("No grammar targets found for cloze nahw.")
            return []

        # Limiter le nombre
        selected = random.sample(targets, min(num_questions, len(targets)))

        questions = []
        for sent, token, rule_type in selected:
            q = self._build_question(sent, token, rule_type, difficulty)
            if q:
                questions.append(q)

        logger.info("Generated {} nahw cloze questions.", len(questions))
        return questions

    def _build_question(self, sent: Sentence, token: Token, rule_type: str,
                        difficulty: str) -> QuestionCloze:
        # Générer l'i3rab
        i3rab_text = self.i3rab.analyze_token(sent, token)

        # Récupérer la règle
        rule_info = db.NAHW_RULES.get(rule_type, {})
        rule_name = rule_info.get("rule_template", rule_type)

        # Créer le trou
        cloze_sent = sent.text.replace(token.text, "............", 1)

        # Vocabulaire de la règle pour l'affichage
        rule_labels = {
            "inna_family": "نواسخ إنّ وأخواتها",
            "kana_family": "نواسخ كان وأخواتها",
            "huruf_jarr": "حروف الجر",
            "maf3ul_bihi": "المفعول به",
        }

        return QuestionCloze(
            id=str(uuid.uuid4())[:8],
            original_sentence=sent.text,
            cloze_sentence=cloze_sent,
            answer=token.bare,
            answer_vocalized=token.text,
            i3rab_rule=rule_labels.get(rule_type, rule_type),
            i3rab_detailed=i3rab_text,
            grammar_category="nahw",
            points=2,
            bloom_level=BloomLevel.APPLY,
            difficulty=DifficultyLevel(difficulty.split(" ")[0]) if " " in difficulty else DifficultyLevel.B1,
        )