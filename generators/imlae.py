# generators/imlae.py
"""Générateur d'exercices d'orthographe (إملاء) — détection d'erreurs."""
import random
import uuid
from typing import List, Tuple
from loguru import logger
from core.nlp_pipeline import NLPPipeline, Sentence
from core.models import QuestionImlae, ImlaeError
from core import linguistics_db as db
import re


class ImlaeGenerator:
    def __init__(self, nlp: NLPPipeline):
        self.nlp = nlp

    def generate(self, sentences: List[Sentence], num_questions: int = 2) -> List[QuestionImlae]:
        questions = []

        # Sélectionner des phrases avec des mots susceptibles d'avoir des erreurs
        candidates = [s for s in sentences if len(s.tokens) > 5]
        if not candidates:
            return questions

        selected = random.sample(candidates, min(num_questions, len(candidates)))

        for sent in selected:
            q = self._inject_errors(sent)
            if q:
                questions.append(q)

        logger.info("Generated {} imlae questions.", len(questions))
        return questions

    def _inject_errors(self, sent: Sentence) -> QuestionImlae:
        """Injecte des erreurs orthographiques dans une phrase."""
        errors = []
        modified_text = sent.text

        # Parcourir les règles d'imlae
        for rule_key, rule_info in db.IMLAE_RULES.items():
            for error_case in rule_info.get("common_errors", []):
                correct = error_case["correct"]
                wrong = error_case["wrong"]

                # Chercher le mot correct dans la phrase
                if correct in modified_text:
                    modified_text = modified_text.replace(correct, wrong, 1)
                    errors.append(ImlaeError(
                        original_word=correct,
                        error_word=wrong,
                        error_type=rule_key,
                        rule_explanation=f"{rule_info['name']}: {error_case['note']}"
                    ))
                    break  # Une erreur par règle par phrase

        if not errors:
            return None

        return QuestionImlae(
            id=str(uuid.uuid4())[:8],
            sentence_with_errors=modified_text,
            errors=errors,
            corrected_sentence=sent.text,
            points=3,
        )