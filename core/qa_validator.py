# core/qa_validator.py
"""
Assurance qualité: valide chaque question générée selon des critères
pédagogiques, linguistiques et psychométriques.
"""
from typing import List, Tuple
from loguru import logger
from core.models import (
    QuestionMCQ, QuestionCloze, QuestionImlae, VocabWord,
    ExamPackage, ExamBlueprint
)
import pyarabic.araby as araby


class QAValidator:

    def validate_exam(self, exam: ExamPackage) -> Tuple[float, List[str]]:
        """
        Valide l'examen complet.
        Retourne (score_qualité 0-100, liste_des_problèmes).
        """
        issues = []
        score = 100.0

        # 1. Vérifier qu'il y a assez de questions
        total_q = (len(exam.questions_mcq) + len(exam.questions_cloze) +
                   len(exam.questions_imlae) + len(exam.questions_vocab))
        if total_q < 5:
            issues.append(f"⚠️ Nombre de questions insuffisant: {total_q} (minimum 5 recommandé)")
            score -= 20

        # 2. Valider chaque QCM
        for i, q in enumerate(exam.questions_mcq):
            q_score, q_issues = self.validate_mcq(q)
            score = (score + q_score) / 2 if i > 0 else (score * 0.7 + q_score * 0.3)
            issues.extend([f"QCM #{i+1}: {iss}" for iss in q_issues])

        # 3. Valider chaque trou (cloze)
        for i, q in enumerate(exam.questions_cloze):
            q_score, q_issues = self.validate_cloze(q)
            issues.extend([f"Trou #{i+1}: {iss}" for iss in q_issues])

        # 4. Vérifier la distribution Bloom
        bloom_dist = self._compute_bloom_distribution(exam)
        if len(bloom_dist) < 2:
            issues.append("⚠️ Distribution Bloom déséquilibrée: tous les exercices sont au même niveau cognitif.")
            score -= 10

        # 5. Vérifier la couverture des compétences
        skill_cov = self._compute_skill_coverage(exam)
        if len(skill_cov) < 2:
            issues.append("⚠️ Couverture de compétences limitée.")
            score -= 10

        # 6. Vérifier les points totaux
        if exam.total_points < 10:
            issues.append(f"⚠️ Barème faible: {exam.total_points} points (minimum 10 recommandé)")
            score -= 5

        score = max(0, min(100, score))
        logger.info("QA Score: {:.1f}/100 — {} issues found", score, len(issues))
        return score, issues

    def validate_mcq(self, q: QuestionMCQ) -> Tuple[float, List[str]]:
        """Valide une question QCM."""
        issues = []
        score = 100.0

        # Exactement une bonne réponse
        correct = [o for o in q.options if o.is_correct]
        if len(correct) != 1:
            issues.append(f"Nombre de réponses correctes: {len(correct)} (doit être 1)")
            score -= 50

        # Au moins 3 options
        if len(q.options) < 3:
            issues.append(f"Options insuffisantes: {len(q.options)} (minimum 3)")
            score -= 20

        # Pas de doublons dans les options
        texts = [araby.strip_tashkeel(o.text) for o in q.options]
        if len(texts) != len(set(texts)):
            issues.append("Options dupliquées détectées")
            score -= 30

        # La question doit avoir du texte
        if len(q.question_text.strip()) < 10:
            issues.append("Texte de question trop court")
            score -= 20

        # Les distracteurs ne doivent pas être évidemment faux
        for opt in q.options:
            if not opt.is_correct and len(opt.text) < 2:
                issues.append(f"Distracteur trop court: '{opt.text}'")
                score -= 10

        return max(0, score), issues

    def validate_cloze(self, q: QuestionCloze) -> Tuple[float, List[str]]:
        """Valide une question à trous."""
        issues = []
        score = 100.0

        # Le trou doit être présent
        if "........" not in q.cloze_sentence:
            issues.append("Trou manquant dans la phrase")
            score -= 40

        # La réponse doit être non vide
        if not q.answer.strip():
            issues.append("Réponse vide")
            score -= 50

        # L'i3rab doit être renseigné
        if not q.i3rab_rule.strip():
            issues.append("Règle d'i3rab manquante")
            score -= 20

        # La phrase originale et à trous doivent avoir la même structure
        if len(q.original_sentence.split()) - len(q.cloze_sentence.split()) > 2:
            issues.append("Différence structurelle entre phrase originale et phrase à trous")
            score -= 15

        return max(0, score), issues

    def _compute_bloom_distribution(self, exam: ExamPackage) -> dict:
        dist = {}
        for q in exam.questions_mcq:
            dist[q.bloom_level.value] = dist.get(q.bloom_level.value, 0) + 1
        for q in exam.questions_cloze:
            dist[q.bloom_level.value] = dist.get(q.bloom_level.value, 0) + 1
        return dist

    def _compute_skill_coverage(self, exam: ExamPackage) -> dict:
        dist = {}
        if exam.questions_mcq:
            dist["comprehension"] = len(exam.questions_mcq)
        if exam.questions_cloze:
            dist["grammar"] = len(exam.questions_cloze)
        if exam.questions_imlae:
            dist["orthography"] = len(exam.questions_imlae)
        if exam.questions_vocab:
            dist["vocabulary"] = len(exam.questions_vocab)
        return dist

    def compute_blueprint(self, exam: ExamPackage) -> ExamBlueprint:
        """Génère le tableau de spécifications."""
        bloom_dist = self._compute_bloom_distribution(exam)
        skill_cov = self._compute_skill_coverage(exam)

        difficulty_dist = {}
        for q in exam.questions_mcq + exam.questions_cloze:
            difficulty_dist[q.difficulty.value] = difficulty_dist.get(q.difficulty.value, 0) + 1

        # Estimation de fiabilité (Cronbach alpha approximatif)
        total_q = (len(exam.questions_mcq) + len(exam.questions_cloze) +
                   len(exam.questions_imlae) + len(exam.questions_vocab))
        # Heuristique: plus de questions et plus de variété → meilleure fiabilité
        variety = len(bloom_dist) * len(skill_cov)
        reliability = min(0.95, 0.5 + (total_q * 0.02) + (variety * 0.03))

        return ExamBlueprint(
            total_questions=total_q,
            bloom_distribution=bloom_dist,
            difficulty_distribution=difficulty_dist,
            skill_coverage=skill_cov,
            estimated_reliability=round(reliability, 3),
        )