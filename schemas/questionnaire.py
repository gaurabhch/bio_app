"""
Pydantic schemas for the PCOS Risk Assessment Questionnaire.
"""

from pydantic import BaseModel, Field, computed_field, model_validator
from typing import Literal, List, Optional, Dict, Any
from uuid import UUID

# ── Section 0
class Section0(BaseModel):
    age: int = Field(..., ge=10, le=60)

# ── Section 1
class Section1(BaseModel):
    height_cm: float = Field(..., gt=100, lt=220)
    weight_kg: float = Field(..., gt=20, lt=300)
    waist_cm: Optional[float] = Field(None, gt=40, lt=200)
    hip_cm: Optional[float] = Field(None, gt=40, lt=200)

    @computed_field
    @property
    def bmi(self) -> float:
        return round(self.weight_kg / (self.height_cm / 100) ** 2, 1)

    @computed_field
    @property
    def whr(self) -> Optional[float]:
        if self.waist_cm and self.hip_cm:
            return round(self.waist_cm / self.hip_cm, 2)
        return None

# ── Section 2
class Section2(BaseModel):
    cycle_length: Literal["lt_21", "21_35", "36_45", "gt_45", "gt_90_or_absent"]
    cycles_per_year: Literal["9_or_more", "5_to_8", "fewer_than_5"]
    ovulation_signs: Literal["yes_regularly", "sometimes", "rarely_never"]
    period_duration: Literal["3_to_7", "lt_3", "gt_7"]
    flow_description: Literal["normal", "light_spotting", "heavy_clots"]
    irregular_onset: Literal["always_since_first", "gradually_worsened", "sudden_onset", "cycles_regular"]
    long_gap_ever: bool
    anovulation_confirmed: Literal["yes_confirmed", "suspected", "no", "unknown"]

# ── Section 3
class MFGSites(BaseModel):
    upper_lip: int = Field(..., ge=0, le=4)
    chin: int = Field(..., ge=0, le=4)
    chest: int = Field(..., ge=0, le=4)
    upper_abdomen: int = Field(..., ge=0, le=4)
    lower_abdomen: int = Field(..., ge=0, le=4)
    upper_arm: int = Field(..., ge=0, le=4)
    thigh: int = Field(..., ge=0, le=4)
    upper_back: int = Field(..., ge=0, le=4)
    lower_back: int = Field(..., ge=0, le=4)

    @computed_field
    @property
    def total(self) -> int:
        return (self.upper_lip + self.chin + self.chest + self.upper_abdomen +
                self.lower_abdomen + self.upper_arm + self.thigh +
                self.upper_back + self.lower_back)

class Section3(BaseModel):
    mfg_sites: MFGSites
    hair_removal: Literal["none", "face_only", "body_only", "both"]
    facial_chin_character: Literal["none", "fine_vellus", "few_terminal_1_5", "noticeable_terminal", "heavy_coarse"]
    body_hair_locations: List[Literal["none", "abdomen_midline", "chest", "upper_back", "lower_back", "upper_arms", "inner_thighs"]]
    acne_frequency: Literal["none", "occasional", "persistent", "severe_cystic"]
    acne_location: Literal["none", "forehead_tzone", "jawline_chin", "both", "back_chest"]
    acne_after_25: Literal["yes", "no", "na"]
    hair_thinning_pattern: Literal["none", "mild_crown_ludwig1", "moderate_ludwig2", "severe_ludwig3", "temples_only", "diffuse"]
    hair_thinning_age_onset: Literal["before_25", "age_25_35", "after_35", "no_thinning"]
    oily_skin: Literal["none", "mild", "severe"]
    oily_scalp: Literal["none", "mild", "severe"]

# ── Section 4
class Section4(BaseModel):
    skin_findings: List[Literal["none", "acanthosis_nigricans", "skin_tags", "both"]]
    thyroid_disorder: Literal["none", "hypothyroidism", "hyperthyroidism", "thyroid_nodule", "never_tested"]
    blood_glucose: Literal["normal", "prediabetes", "type2_diabetes", "gestational_prior", "never_tested"]
    lipid_profile: Literal["normal", "high_tg_low_hdl", "high_ldl", "multiple_abnormalities", "never_tested"]
    blood_pressure: Literal["normal", "elevated", "high", "unknown"]
    family_history: List[Literal["none", "pcos_mother_sister", "t2dm_metabolic", "cvd_before_60", "multiple"]]
    sleep_apnea: List[Literal["none", "snoring", "waking_unrefreshed", "daytime_sleepiness", "diagnosed_osa"]]
    hormonal_status: Literal["normal", "elevated_prolactin", "elevated_dheas_androstenedione", "cah_diagnosed", "never_tested"]

# ── Section 5
class Section5(BaseModel):
    anxiety: Literal["none", "mild", "moderate", "severe", "diagnosed"]
    depression: Literal["none", "mild", "moderate", "severe", "diagnosed"]
    body_image: Literal["none", "mild", "moderate", "severe"]
    psychosexual: List[Literal["none", "reduced_libido", "body_image_intimacy", "physical_barrier", "multiple"]]
    disordered_eating: Literal["none", "restrictive", "binge_eating", "compensatory", "diagnosed_eating_disorder"]

# ── Section 6
class Section6(BaseModel):
    physical_activity: Literal["sedentary", "light", "moderate", "active", "very_active"]
    dietary_pattern: Literal["high_gi", "mixed", "low_gi", "balanced_veg_vegan", "high_protein_low_carb"]
    stress_level: Literal["low", "moderate", "high", "chronic_burnout"]
    sleep_quality: Literal["good", "disturbed", "short", "diagnosed_disorder"]
    smoking: Literal["never", "former", "current"]
    alcohol: Literal["none", "occasional", "moderate", "heavy"]

# ── Section 7
class Section7(BaseModel):
    fertility_intent: Literal["not_trying", "trying_succeeding", "trying_6mo_no_success", "anovulatory_infertility", "tubal_male_factor"]
    prior_pregnancies: Literal["none", "one_or_more_successful", "one_or_more_miscarriage", "recurrent_miscarriage"]
    gestational_diabetes: Literal["yes", "no", "na"]
    hormonal_contraception: Literal["not_using", "combined_pill", "progestin_only", "hormonal_iud", "stopped_last_3mo"]

# ── Full Submit
class QuestionnaireSubmitRequest(BaseModel):
    section_0: Section0
    section_1: Section1
    section_2: Section2
    section_3: Section3
    section_4: Section4
    section_5: Section5
    section_6: Section6
    section_7: Section7

# ── Progress Save
class SaveProgressRequest(BaseModel):
    current_step: int = Field(..., ge=0, le=100)
    partial_data: Dict[str, Any]

class ClinicalFlag(BaseModel):
    priority: int           # 1=CRITICAL, 2=HIGH, 3=MODERATE, 4=SUPPORTIVE
    category: str
    message: str
    action: str

class RotterdamCriterion(BaseModel):
    result: str
    confidence: str
    signals: List[str]


class ScoringResultResponse(BaseModel):
    composite_score: int
    risk_tier: str
    criterion_1: RotterdamCriterion
    criterion_2: RotterdamCriterion
    criterion_3: str
    phenotype: str
    phenotype_confidence: str
    mfg_total: int
    mfg_corrected: int
    mfg_grade: str
    ludwig_grade: int
    ha_composite: int
    oligo_score: int
    differential_flags: List[Dict]
    clinical_flags: List[ClinicalFlag]
    recommended_investigations: List[str]
    not_recommended: List[Dict[str, str]]

class AssessmentSubmitResponse(ScoringResultResponse):
    assessment_id: str
