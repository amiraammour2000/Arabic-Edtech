# core/engine.py
"""
Moteur principal: orchestre le pipeline NLP, les générateurs,
la validation QA et la construction du package d'examen.
"""
import uuid
from typing import Dict, List
from loguru import logger
from core.nlp_pipeline import NLPPipeline
from core.i3rab_engine import I3rabEngine
from core.distractor_engine import DistractorEngine
from core.qa_validator import QAValidator
from core.security import SecurityService
from core.models import (
    ExamPackage, ExamMetadata, DifficultyLevel,
    QuestionMCQ, QuestionCloze, QuestionImlae, VocabWord
)
from generators.mcq_comprehension import MCQComprehensionGenerator
from generators.cloze_nahw import ClozeNahwGenerator
from generators.cloze_sarf import ClozeSarfGenerator
from generators.imlae import ImlaeGenerator
from generators.vocab_extract import VocabExtractGenerator


class ExamEngine:
    def __init__(self):
        self.nlp = NLPPipeline()
        self.i3rab = I3rabEngine(self.nlp)
        self.distractors = DistractorEngine(self.nlp)
        self.qa = QAValidator()

        # Générateurs
        self.gen_mcq = MCQComprehensionGenerator(self.nlp, self.distractors)
        self.gen_nahw = ClozeNahwGenerator(self.nlp, self.i3rab)
        self.gen_sarf = ClozeSarfGenerator(self.nlp)
        self.gen_imlae = ImlaeGenerator(self.nlp)
        self.gen_vocab = VocabExtractGenerator(self.nlp)

        logger.info("ExamEngine v3.0 initialized — full pipeline ready.")

    def build_exam(self, raw_text: str, config: Dict,
                   metadata: ExamMetadata = None) -> ExamPackage:
        logger.info("Building exam with config: {}", config)

        if metadata is None:
            metadata = ExamMetadata()

        # 1. Pipeline NLP
        sentences = self.nlp.process(raw_text)
        if not sentences:
            raise ValueError("Le texte fourni n'a pas pu être analysé.")

        # 2. Vocalisation
        vocalized = " ".join(s.text for s in sentences)

        # 3. Génération des questions
        difficulty = config.get("difficulty", "B1 - المتوسط")
        diff_code = difficulty.split(" ")[0] if " " in difficulty else "B1"

        questions_mcq = []
        questions_cloze = []
        questions_imlae = []
        questions_vocab = []

        if config.get("mcq", True) and config.get("num_mcq", 3) > 0:
            questions_mcq = self.gen_mcq.generate(
                sentences, config["num_mcq"], diff_code
            )

        if config.get("cloze_nahw", True):
            questions_cloze.extend(
                self.gen_nahw.generate(sentences, config.get("num_nahw", 5), diff_code)
            )

        if config.get("cloze_sarf", False):
            questions_cloze.extend(
                self.gen_sarf.generate(sentences, config.get("num_sarf", 3), diff_code)
            )

        if config.get("imlae", False):
            questions_imlae = self.gen_imlae.generate(
                sentences, config.get("num_imlae", 2)
            )

        if config.get("vocab", False):
            questions_vocab = self.gen_vocab.generate(
                sentences, config.get("num_vocab", 5)
            )

        # 4. Calcul du barème
        total_points = (
            sum(q.points for q in questions_mcq) +
            sum(q.points for q in questions_cloze) +
            sum(q.points for q in questions_imlae) +
            sum(q.points for q in questions_vocab)
        )

        # 5. Hash de sécurité
        security_hash = SecurityService.generate_hash(raw_text)

        # 6. QR Code
        qr_data = f"EXAM:{security_hash[:16]}|PTS:{total_points}|Q:{len(questions_mcq + questions_cloze + questions_imlae + questions_vocab)}"
        qr_b64 = SecurityService.generate_qr_code(qr_data)

        # 7. Construction du package
        package = ExamPackage(
            id=str(uuid.uuid4()),
            metadata=metadata,
            vocalized_text=vocalized,
            raw_text=raw_text,
            questions_mcq=questions_mcq,
            questions_cloze=questions_cloze,
            questions_imlae=questions_imlae,
            questions_vocab=questions_vocab,
            total_points=total_points,
            security_hash=security_hash,
            qr_code_b64=qr_b64,
            watermark_text="ARABIC EDTECH PRO",
        )

        # 8. QA Validation
        score, issues = self.qa.validate_exam(package)
        package.quality_score = score

        # 9. Blueprint
        package.blueprint = self.qa.compute_blueprint(package)

        # Logger les issues
        for issue in issues:
            logger.warning("QA Issue: {}", issue)

        logger.success(
            "Exam built: {} MCQ, {} Cloze, {} Imlae, {} Vocab | {} pts | QA: {:.1f}",
            len(questions_mcq), len(questions_cloze),
            len(questions_imlae), len(questions_vocab),
            total_points, score
        )

        return package