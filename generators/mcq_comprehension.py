# generators/mcq_comprehension.py
"""Générateur de QCM de compréhension de texte."""
import random
import uuid
from typing import List
from loguru import logger
from core.nlp_pipeline import NLPPipeline, Sentence, Token
from core.models import QuestionMCQ, MCQOption, DifficultyLevel, BloomLevel
from core.distractor_engine import DistractorEngine
from core import linguistics_db as db
import pyarabic.araby as araby


class MCQComprehensionGenerator:
    def __init__(self, nlp: NLPPipeline, distractor_engine: DistractorEngine):
        self.nlp = nlp
        self.distractors = distractor_engine

    def generate(self, sentences: List[Sentence], num_questions: int,
                 difficulty: str = "B1") -> List[QuestionMCQ]:
        questions = []

        # Filtrer les phrases avec assez de contenu
        candidates = [s for s in sentences if len(s.tokens) > 6]
        if not candidates:
            logger.warning("No suitable sentences for MCQ comprehension.")
            return questions

        # Sélectionner des phrases variées
        selected = random.sample(candidates, min(num_questions, len(candidates)))

        for sent in selected:
            q = self._generate_from_sentence(sent, difficulty)
            if q:
                questions.append(q)

        logger.info("Generated {} comprehension MCQs.", len(questions))
        return questions

    def _generate_from_sentence(self, sent: Sentence, difficulty: str) -> QuestionMCQ:
        """Génère une question de compréhension à partir d'une phrase."""
        # Cibler un nom ou verbe important (pas stop word, pas trop court)
        targets = [
            t for t in sent.tokens
            if t.bare not in db.STOP_WORDS
            and len(t.bare) > 3
            and t.pos in ("noun", "verb", "adj", "N", "V", "ADJ")
            and not t.bare.startswith("و")
            and not t.bare.startswith("ف")
        ]

        if not targets:
            return None

        target = random.choice(targets)
        bare = target.bare

        # Générer les distracteurs
        distractor_list = self.distractors.generate_distractors(
            target_word=bare,
            target_pos=target.pos,
            target_root=target.root,
            count=3,
            difficulty=difficulty
        )

        # Construire les options
        options = [MCQOption(text=bare, is_correct=True, distractor_type="correct")]
        for d in distractor_list:
            options.append(MCQOption(text=d, is_correct=False, distractor_type="semantic"))

        random.shuffle(options)

        # Créer la question avec un blanc
        question_text = sent.text.replace(target.text, "______", 1)

        # Explication
        explanation = f"الكلمة الصحيحة هي «{bare}» لأنها تتناسب مع سياق الجملة ومعنىها."

        return QuestionMCQ(
            id=str(uuid.uuid4())[:8],
            question_text=question_text,
            context_sentence=sent.text,
            options=options,
            points=1,
            bloom_level=BloomLevel.UNDERSTAND,
            difficulty=DifficultyLevel(difficulty.split(" ")[0]) if " " in difficulty else DifficultyLevel.B1,
            cefr_level=difficulty.split(" ")[0] if " " in difficulty else "B1",
            skill_targeted="comprehension",
            explanation=explanation,
            source_word=bare,
            source_pos=target.pos,
        )