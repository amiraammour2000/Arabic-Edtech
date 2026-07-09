# core/models.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Literal
from enum import Enum
from datetime import datetime


class DifficultyLevel(str, Enum):
    A1 = "A1 - مبتدئ"
    A2 = "A2 - ما قبل المتوسط"
    B1 = "B1 - المتوسط"
    B2 = "B2 - فوق المتوسط"
    C1 = "C1 - المتقدم"
    C2 = "C2 - الإتقان"


class BloomLevel(str, Enum):
    REMEMBER = "تذكر"
    UNDERSTAND = "فهم"
    APPLY = "تطبيق"
    ANALYZE = "تحليل"
    EVALUATE = "تقييم"
    CREATE = "إبداع"


class ExerciseType(str, Enum):
    MCQ_COMPREHENSION = "qcm_comprehension"
    MCQ_VOCABULARY = "qcm_vocabulaire"
    CLOZE_NAHW = "trou_nahw"
    CLOZE_SARF = "trou_sarf"
    IMLAE = "imlae"
    VOCAB_EXTRACT = "extraction_vocabulaire"


class MCQOption(BaseModel):
    text: str
    is_correct: bool = False
    distractor_type: Optional[str] = None  # root, semantic, morphological, random


class QuestionMCQ(BaseModel):
    id: str
    question_text: str
    context_sentence: Optional[str] = None
    options: List[MCQOption]
    points: int = 1
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND
    difficulty: DifficultyLevel = DifficultyLevel.B1
    cefr_level: str = "B1"
    skill_targeted: str = "comprehension"
    explanation: str = ""
    source_word: Optional[str] = None
    source_pos: Optional[str] = None


class QuestionCloze(BaseModel):
    id: str
    original_sentence: str
    cloze_sentence: str
    answer: str
    answer_vocalized: str
    i3rab_rule: str
    i3rab_detailed: str  # إعراب مفصّل
    grammar_category: str  # nahw, sarf
    points: int = 2
    bloom_level: BloomLevel = BloomLevel.APPLY
    difficulty: DifficultyLevel = DifficultyLevel.B1


class ImlaeError(BaseModel):
    original_word: str
    error_word: str
    error_type: str  # hamza_wasl, hamza_qat3, taa_marbuta, alif_maqsura, etc.
    rule_explanation: str


class QuestionImlae(BaseModel):
    id: str
    sentence_with_errors: str
    errors: List[ImlaeError]
    corrected_sentence: str
    points: int = 3
    bloom_level: BloomLevel = BloomLevel.ANALYZE


class VocabWord(BaseModel):
    word: str
    vocalized: str
    root: Optional[str] = None
    pos: Optional[str] = None
    definition: Optional[str] = None
    context_sentence: str
    synonyms: List[str] = []
    antonyms: List[str] = []
    points: int = 1


class ExamMetadata(BaseModel):
    title: str = "اختبار في اللغة العربية"
    institution: str = ""
    teacher: str = ""
    student_name_field: bool = True
    student_class_field: bool = True
    date_field: bool = True
    duration_minutes: int = 60
    instructions: str = "اقرأ النص بعناية ثم أجب عن الأسئلة بدقة."
    academic_year: str = ""


class ExamBlueprint(BaseModel):
    """Tableau de spécifications — garantit la validité pédagogique."""
    total_questions: int
    bloom_distribution: Dict[str, int]
    difficulty_distribution: Dict[str, int]
    skill_coverage: Dict[str, int]
    estimated_reliability: float  # Cronbach alpha estimate


class ExamPackage(BaseModel):
    id: str
    metadata: ExamMetadata
    vocalized_text: str
    raw_text: str
    questions_mcq: List[QuestionMCQ] = []
    questions_cloze: List[QuestionCloze] = []
    questions_imlae: List[QuestionImlae] = []
    questions_vocab: List[VocabWord] = []
    total_points: int = 0
    security_hash: str
    qr_code_b64: str = ""
    watermark_text: str = ""
    blueprint: Optional[ExamBlueprint] = None
    quality_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("total_points")
    @classmethod
    def validate_points(cls, v, info):
        if v <= 0:
            raise ValueError("Total points must be positive")
        return v