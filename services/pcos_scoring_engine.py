from typing import List, Dict, Tuple

from schemas.questionnaire import (
    QuestionnaireSubmitRequest,
    ScoringResultResponse,
    ClinicalFlag,
    RotterdamCriterion,
)


class PCOSScoringEngine:
    def score(self, data: QuestionnaireSubmitRequest) -> ScoringResultResponse:
        differential_flags: List[Dict] = []
        clinical_flags: List[ClinicalFlag] = []

        self._stage0_age_flags(data, differential_flags)
        self._stage1_disqualifiers(data, differential_flags, clinical_flags)

        oligo_score, c1_result, c1_confidence, c1_signals = self._stage2_criterion1(data.section_2)

        (
            mfg_total,
            mfg_corrected,
            mfg_grade,
            ludwig_grade,
            ha_composite,
            c2_clinical_result,
            c2_confidence,
            c2_signals,
            criterion_2_resolution,
        ) = self._stage3_criterion2(data.section_3)

        criterion_3 = (
            "UNKNOWN — REQUIRES PELVIC ULTRASOUND "
            "(TVS preferred; if not acceptable, transabdominal ultrasound)"
        )

        phenotype, phenotype_confidence = self._stage5_phenotype(
            c1_result, criterion_2_resolution
        )

        composite_score = self._stage6_composite(
            data, c1_result, criterion_2_resolution
        )

        risk_tier = self._risk_tier(composite_score)

        self._stage7_clinical_flags(
            data=data,
            c1_result=c1_result,
            c2_resolution=criterion_2_resolution,
            c1_signals=c1_signals,
            c2_signals=c2_signals,
            composite_score=composite_score,
            clinical_flags=clinical_flags,
        )

        recommended_investigations, not_recommended = self._stage8_investigations(
            data=data,
            c1_result=c1_result,
            c2_resolution=criterion_2_resolution,
            c2_signals=c2_signals,
        )

        clinical_flags = self._sort_and_dedupe_flags(clinical_flags)

        criterion_1 = RotterdamCriterion(
            result=c1_result,
            confidence=c1_confidence,
            signals=c1_signals,
        )

        criterion_2 = RotterdamCriterion(
            result=criterion_2_resolution,
            confidence=c2_confidence,
            signals=c2_signals,
        )

        return ScoringResultResponse(
            composite_score=composite_score,
            risk_tier=risk_tier,
            criterion_1=criterion_1,
            criterion_2=criterion_2,
            criterion_3=criterion_3,
            phenotype=phenotype,
            phenotype_confidence=phenotype_confidence,
            mfg_total=mfg_total,
            mfg_corrected=mfg_corrected,
            mfg_grade=mfg_grade,
            ludwig_grade=ludwig_grade,
            ha_composite=ha_composite,
            oligo_score=oligo_score,
            differential_flags=differential_flags,
            clinical_flags=clinical_flags,
            recommended_investigations=self._dedupe_strings(recommended_investigations),
            not_recommended=not_recommended,
        )

    def _stage0_age_flags(self, data: QuestionnaireSubmitRequest, differential_flags: List[Dict]) -> None:
        age = data.section_0.age

        if age < 18:
            differential_flags.append({
                "severity": "HIGH",
                "category": "AGE_SCOPE",
                "message": "Age is below 18 years. Adult PCOS questionnaire interpretation is outside intended range.",
                "action": "Use adolescent protocol; interpret menstrual irregularity and hyperandrogenism using age-appropriate guidance."
            })
        elif age > 40:
            differential_flags.append({
                "severity": "HIGH",
                "category": "AGE_SCOPE",
                "message": "Age is above 40 years. Perimenopausal considerations may confound interpretation.",
                "action": "Use perimenopausal differential framework before labeling as PCOS."
            })

    def _stage1_disqualifiers(
        self,
        data: QuestionnaireSubmitRequest,
        differential_flags: List[Dict],
        clinical_flags: List[ClinicalFlag],
    ) -> None:
        s2 = data.section_2
        s4 = data.section_4
        s7 = data.section_7

        if s4.thyroid_disorder == "hypothyroidism":
            differential_flags.append({
                "severity": "CRITICAL",
                "category": "DIFFERENTIAL",
                "message": "Hypothyroidism must be excluded as primary cause — TSH, fT3, fT4 required.",
                "action": "Do not label as PCOS until thyroid status is addressed."
            })

        if s4.thyroid_disorder == "never_tested":
            differential_flags.append({
                "severity": "HIGH",
                "category": "DIFFERENTIAL",
                "message": "Thyroid status unknown — thyroid screening is mandatory before PCOS workup.",
                "action": "Order TSH and free T4."
            })

        if s4.hormonal_status == "elevated_prolactin":
            differential_flags.append({
                "severity": "CRITICAL",
                "category": "DIFFERENTIAL",
                "message": "Hyperprolactinemia can cause anovulation and must be excluded before diagnosing PCOS.",
                "action": "Repeat fasting prolactin if needed and arrange pituitary workup / MRI as clinically indicated."
            })

        if s4.hormonal_status == "cah_diagnosed":
            differential_flags.append({
                "severity": "CRITICAL",
                "category": "DIFFERENTIAL",
                "message": "Congenital adrenal hyperplasia is a primary exclusion criterion for PCOS.",
                "action": "PCOS diagnosis is not applicable unless CAH diagnosis is revised."
            })

        if s7.hormonal_contraception in [
            "combined_pill",
            "progestin_only",
            "hormonal_iud",
            "stopped_last_3mo",
        ]:
            differential_flags.append({
                "severity": "HIGH",
                "category": "CONFOUNDER",
                "message": "Hormonal contraception alters SHBG and androgen-related assessment; biochemical hyperandrogenism cannot be reliably assessed now.",
                "action": "Withhold biochemical androgen interpretation until at least 3 months after stopping hormonal contraception."
            })

        if s2.irregular_onset == "sudden_onset":
            differential_flags.append({
                "severity": "MODERATE",
                "category": "DIFFERENTIAL",
                "message": "Sudden-onset menstrual irregularity suggests possible non-PCOS pathology.",
                "action": "Broaden differential diagnosis for thyroid, pituitary, structural, or other causes."
            })

        if s4.hormonal_status == "never_tested":
            clinical_flags.append(
                ClinicalFlag(
                    priority=3,
                    category="SCREENING",
                    message="Prolactin / adrenal differential status has never been tested.",
                    action="Check prolactin; consider DHEAS / androstenedione and 17-OHP when clinically indicated."
                )
            )

    def _stage2_criterion1(self, s2) -> Tuple[int, str, str, List[str]]:
        score = 0
        signals: List[str] = []

        if s2.cycle_length == "gt_90_or_absent":
            score += 40
            signals.append("Cycle length >90 days or amenorrhea")
        elif s2.cycle_length == "gt_45":
            score += 40
            signals.append("Cycle length >45 days")
        elif s2.cycle_length == "36_45":
            score += 15
            signals.append("Slightly irregular cycle length 36–45 days")
        elif s2.cycle_length == "lt_21":
            score += 15
            signals.append("Cycle length <21 days")

        if s2.cycles_per_year == "fewer_than_5":
            score += 40
            signals.append("Fewer than 5 cycles per year")
        elif s2.cycles_per_year == "5_to_8":
            score += 25
            signals.append("5–8 cycles per year (below 8-cycle threshold)")

        if s2.ovulation_signs == "rarely_never":
            score += 15
            signals.append("No mid-cycle ovulatory symptoms")
        elif s2.ovulation_signs == "sometimes":
            score += 7
            signals.append("Only occasional ovulation signs")

        if s2.long_gap_ever:
            score += 40
            signals.append("Any single cycle >90 days reported")

        if s2.anovulation_confirmed == "yes_confirmed":
            score += 50
            signals.append("Clinician-confirmed anovulation")
        elif s2.anovulation_confirmed == "suspected":
            score += 10
            signals.append("Anovulation suspected but not confirmed")

        if s2.flow_description == "light_spotting":
            score += 5
            signals.append("Light or spotting flow")

        if s2.period_duration == "lt_3":
            score += 5
            signals.append("Scanty / short bleeding duration <3 days")

        if s2.irregular_onset == "always_since_first":
            score += 10
            signals.append("Irregular cycles since menarche")

        if score >= 40:
            return score, "POSITIVE", "HIGH" if score >= 60 else "MODERATE", signals
        if score >= 20:
            signals.append("Possible oligo-anovulation — serum progesterone mid-luteal (day 21) recommended for confirmation")
            return score, "UNCERTAIN", "LOW", signals
        return score, "NEGATIVE", "LOW", signals

    def _stage3_criterion2(self, s3) -> Tuple[int, int, str, int, int, str, str, List[str], str]:
        signals: List[str] = []

        mfg_total = s3.mfg_sites.total
        mfg_subscore = 0

        if mfg_total >= 8:
            mfg_grade = "SEVERE"
            mfg_subscore = 40
        elif mfg_total >= 4:
            mfg_grade = "MILD_MODERATE"
            mfg_subscore = 25
        elif mfg_total >= 2:
            mfg_grade = "BORDERLINE"
            mfg_subscore = 10
        else:
            mfg_grade = "NONE"

        mfg_corrected = mfg_total
        if s3.hair_removal in ["face_only", "body_only", "both"]:
            mfg_subscore = min(mfg_subscore + 10, 40)
            mfg_corrected = min(mfg_total + 10, 36)
            signals.append("mFG likely underestimated due to self-treatment — clinician reassessment of terminal hair sites recommended")

        if mfg_grade != "NONE":
            signals.append(f"mFG total {mfg_total}, corrected {mfg_corrected}, grade {mfg_grade}")

        acne_subscore = 0
        if s3.acne_location in ["jawline_chin", "both"]:
            acne_subscore += 20
            signals.append("Jawline/chin acne pattern suggests androgen-dependent acne")
            if s3.acne_frequency == "severe_cystic":
                acne_subscore += 10
        elif s3.acne_location == "forehead_tzone":
            acne_subscore += 5
        elif s3.acne_location == "back_chest":
            acne_subscore += 10
            signals.append("Back/chest acne present")

        if s3.acne_after_25 == "yes":
            acne_subscore += 8
            signals.append("Adult-onset or worsening acne after age 25")

        alopecia_subscore = 0
        ludwig_grade = self._get_ludwig_grade(s3.hair_thinning_pattern)

        if ludwig_grade == 3:
            alopecia_subscore = 25
            signals.append("Ludwig grade III crown alopecia")
        elif ludwig_grade == 2:
            alopecia_subscore = 18
            signals.append("Ludwig grade II crown alopecia")
        elif ludwig_grade == 1:
            alopecia_subscore = 10
            signals.append("Ludwig grade I crown alopecia")

        if s3.hair_thinning_pattern == "diffuse":
            alopecia_subscore = max(0, alopecia_subscore - 8)
            signals.append("Diffuse alopecia is non-specific — thyroid disorder and iron deficiency should be excluded")
        elif s3.hair_thinning_pattern == "temples_only":
            alopecia_subscore = max(0, alopecia_subscore - 5)
            signals.append("Temples-only thinning is less specific for androgenic alopecia")

        support_subscore = 0

        if s3.facial_chin_character == "heavy_coarse":
            support_subscore += 15
            signals.append("Heavy/coarse facial hair")
        elif s3.facial_chin_character == "noticeable_terminal":
            support_subscore += 10
            signals.append("Noticeable terminal facial hair")
        elif s3.facial_chin_character == "few_terminal_1_5":
            support_subscore += 4
            signals.append("Few terminal facial hairs")

        body_sites = [x for x in s3.body_hair_locations if x != "none"]
        if any(site in body_sites for site in ["chest", "upper_back", "lower_back"]):
            support_subscore += 12
            signals.append("Body hair at androgenic sites")
        elif "abdomen_midline" in body_sites:
            support_subscore += 6
            signals.append("Linea alba / abdominal midline hair")
        elif body_sites:
            support_subscore += 4
            signals.append("Additional body hair noted")

        if s3.oily_skin == "severe":
            support_subscore += 5
        elif s3.oily_skin == "mild":
            support_subscore += 2

        if s3.oily_scalp == "severe":
            support_subscore += 4

        ha_composite = mfg_subscore + acne_subscore + alopecia_subscore + support_subscore

        if ha_composite >= 30:
            c2_clinical = "POSITIVE"
            c2_confidence = "HIGH" if ha_composite >= 50 else "MODERATE"
        elif ha_composite >= 15:
            c2_clinical = "UNCERTAIN"
            c2_confidence = "LOW"
            signals.append("Borderline clinical hyperandrogenism — biochemical testing essential")
        else:
            c2_clinical = "NEGATIVE"
            c2_confidence = "LOW"

        signals.append(
            "Biochemical confirmation required: free testosterone by LC-MS/MS preferred, or total testosterone + SHBG with FAI / calculated free testosterone; direct free testosterone immunoassays are unreliable"
        )

        if c2_clinical == "POSITIVE":
            criterion_2_resolution = "LIKELY_POSITIVE"
        elif c2_clinical == "UNCERTAIN":
            criterion_2_resolution = "POSSIBLE"
        else:
            criterion_2_resolution = "LIKELY_NEGATIVE"

        return (
            mfg_total,
            mfg_corrected,
            mfg_grade,
            ludwig_grade,
            ha_composite,
            c2_clinical,
            c2_confidence,
            signals,
            criterion_2_resolution,
        )

    def _stage5_phenotype(self, c1_result: str, c2_resolution: str) -> Tuple[str, str]:
        if c1_result == "POSITIVE" and c2_resolution == "LIKELY_POSITIVE":
            return (
                "A_OR_B",
                "HIGH — Criteria 1 and 2 met; ultrasound determines Phenotype A vs B",
            )
        if c1_result == "POSITIVE" and c2_resolution == "LIKELY_NEGATIVE":
            return (
                "D_POSSIBLE",
                "MODERATE — Phenotype D possible if PCOM is confirmed; biochemical HA still needs exclusion",
            )
        if c1_result == "NEGATIVE" and c2_resolution == "LIKELY_POSITIVE":
            return (
                "C_POSSIBLE",
                "MODERATE — Phenotype C possible if PCOM is confirmed on ultrasound",
            )
        return (
            "INDETERMINATE",
            "LOW — Insufficient evidence for phenotype classification without further investigation",
        )

    def _stage6_composite(self, data: QuestionnaireSubmitRequest, c1_result: str, c2_resolution: str) -> int:
        s1 = data.section_1
        s4 = data.section_4
        s6 = data.section_6

        composite = 0

        if c1_result == "POSITIVE":
            composite += 30
        elif c1_result == "UNCERTAIN":
            composite += 15

        if c2_resolution == "LIKELY_POSITIVE":
            composite += 25
        elif c2_resolution == "POSSIBLE":
            composite += 12

        if s1.bmi >= 30:
            composite += 10
        elif s1.bmi >= 25:
            composite += 6
        elif s1.bmi >= 23:
            composite += 3

        if s1.whr is not None:
            if s1.whr > 0.87:
                composite += 5
            elif s1.whr > 0.80:
                composite += 2

        if "acanthosis_nigricans" in s4.skin_findings or "both" in s4.skin_findings:
            composite += 7

        if s4.blood_glucose == "type2_diabetes":
            composite += 5
        elif s4.blood_glucose == "prediabetes":
            composite += 3
        elif s4.blood_glucose == "gestational_prior":
            composite += 2

        if s4.lipid_profile in ["high_tg_low_hdl", "multiple_abnormalities"]:
            composite += 3

        if s4.blood_pressure == "high":
            composite += 3
        elif s4.blood_pressure == "elevated":
            composite += 1

        if "multiple" in s4.family_history:
            composite += 8
        elif "pcos_mother_sister" in s4.family_history:
            composite += 6
        elif "t2dm_metabolic" in s4.family_history:
            composite += 3
        elif "cvd_before_60" in s4.family_history:
            composite += 2

        lifestyle_modifier = 0
        if s6.physical_activity == "sedentary":
            lifestyle_modifier += 3
        elif s6.physical_activity == "light":
            lifestyle_modifier += 1
        elif s6.physical_activity == "very_active":
            lifestyle_modifier -= 2

        if s6.dietary_pattern == "high_gi":
            lifestyle_modifier += 2
        elif s6.dietary_pattern == "low_gi":
            lifestyle_modifier -= 1

        if s6.stress_level == "chronic_burnout":
            lifestyle_modifier += 2
        elif s6.stress_level == "high":
            lifestyle_modifier += 1

        composite += max(0, min(7, lifestyle_modifier))
        return min(100, composite)

    def _stage7_clinical_flags(
        self,
        data: QuestionnaireSubmitRequest,
        c1_result: str,
        c2_resolution: str,
        c1_signals: List[str],
        c2_signals: List[str],
        composite_score: int,
        clinical_flags: List[ClinicalFlag],
    ) -> None:
        s1 = data.section_1
        s3 = data.section_3
        s4 = data.section_4
        s5 = data.section_5
        s6 = data.section_6
        s7 = data.section_7

        if s4.blood_glucose == "type2_diabetes":
            clinical_flags.append(ClinicalFlag(
                priority=2,
                category="METABOLIC",
                message="Type 2 diabetes reported — urgent metabolic co-management is required.",
                action="Arrange HbA1c, confirm glucose status, and refer for endocrinology / physician management."
            ))

        if s4.blood_pressure == "high":
            clinical_flags.append(ClinicalFlag(
                priority=2,
                category="CARDIOVASCULAR",
                message="Blood pressure is in the high range (≥140/90 mmHg).",
                action="Start cardiovascular risk assessment and ensure repeat / ambulatory BP monitoring."
            ))

        if "acanthosis_nigricans" in s4.skin_findings or "both" in s4.skin_findings:
            clinical_flags.append(ClinicalFlag(
                priority=2,
                category="INSULIN_RESISTANCE",
                message="Acanthosis nigricans is a strong clinical marker of insulin resistance.",
                action="Arrange OGTT and metabolic risk assessment."
            ))

        if s7.fertility_intent == "anovulatory_infertility":
            clinical_flags.append(ClinicalFlag(
                priority=2,
                category="FERTILITY",
                message="Confirmed anovulatory infertility is present.",
                action="Refer to reproductive endocrinology; ovulation induction assessment is appropriate."
            ))

        if s5.anxiety in ["severe", "diagnosed"] or s5.depression in ["severe", "diagnosed"]:
            clinical_flags.append(ClinicalFlag(
                priority=2,
                category="MENTAL_HEALTH",
                message="Severe or diagnosed anxiety/depression is present.",
                action="Refer to a qualified mental health professional alongside PCOS management."
            ))

        if s4.blood_glucose in ["prediabetes", "never_tested"]:
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="METABOLIC_SCREENING",
                message="Baseline glucose assessment is needed or already abnormal.",
                action="Arrange 75 g OGTT at baseline; repeat periodically according to risk profile."
            ))

        if s4.thyroid_disorder == "never_tested":
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="SCREENING",
                message="Thyroid function has never been tested.",
                action="Order TSH and free T4."
            ))

        if s3.hair_removal in ["face_only", "body_only", "both"]:
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="CLINICAL_HIRSUTISM",
                message="Hirsutism severity may be underestimated because of regular hair removal.",
                action="Arrange clinical reassessment of hirsutism sites after a period without removal, if feasible."
            ))

        if s7.hormonal_contraception in ["combined_pill", "progestin_only", "hormonal_iud", "stopped_last_3mo"]:
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="ASSESSMENT_LIMITATION",
                message="Hormonal contraception limits biochemical androgen interpretation.",
                action="Reassess biochemical hyperandrogenism only after adequate washout."
            ))

        osa_symptom_count = len(
            [x for x in s4.sleep_apnea if x in ["snoring", "waking_unrefreshed", "daytime_sleepiness"]]
        )
        if "diagnosed_osa" in s4.sleep_apnea:
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="SLEEP",
                message="Diagnosed obstructive sleep apnea is present.",
                action="Review sleep management and comorbidity burden."
            ))
        elif osa_symptom_count >= 2:
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="SLEEP",
                message="Two or more sleep apnea symptoms are present.",
                action="Administer Berlin Questionnaire and consider referral for sleep evaluation."
            ))

        if "pcos_mother_sister" in s4.family_history or "multiple" in s4.family_history:
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="FAMILY_HISTORY",
                message="Family history increases pre-test probability of PCOS-related pathology.",
                action="Use a lower threshold for full Rotterdam workup."
            ))

        if s1.bmi >= 23:
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="ANTHROPOMETRIC",
                message=f"BMI {s1.bmi} is above the South Asian elevated-risk threshold.",
                action="Provide structured lifestyle counselling and weight-management support where appropriate."
            ))

        if s1.whr is not None and s1.whr > 0.87:
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="CENTRAL_ADIPOSITY",
                message=f"WHR {s1.whr} suggests significant central adiposity.",
                action="Escalate cardiometabolic risk screening and counselling."
            ))
        elif s1.whr is not None and s1.whr > 0.80:
            clinical_flags.append(ClinicalFlag(
                priority=4,
                category="CENTRAL_ADIPOSITY",
                message=f"WHR {s1.whr} is above the lower central adiposity threshold.",
                action="Track waist-based risk over time and reinforce lifestyle measures."
            ))

        if s6.physical_activity == "sedentary" and s6.dietary_pattern == "high_gi":
            clinical_flags.append(ClinicalFlag(
                priority=4,
                category="LIFESTYLE",
                message="Sedentary activity plus high-GI diet is a major modifiable driver of metabolic risk.",
                action="Target at least 150 minutes/week of moderate activity and shift toward lower-GI intake."
            ))

        if s5.disordered_eating in ["binge_eating", "compensatory", "diagnosed_eating_disorder"]:
            clinical_flags.append(ClinicalFlag(
                priority=4,
                category="EATING_BEHAVIOUR",
                message="Disordered eating behaviour is present.",
                action="Refer to a dietitian and mental health professional experienced in eating disorders."
            ))

        if s7.fertility_intent == "trying_6mo_no_success":
            clinical_flags.append(ClinicalFlag(
                priority=4,
                category="FERTILITY",
                message="Trying to conceive for 6 or more months without success.",
                action="Refer for fertility evaluation, including partner factors where relevant."
            ))

        if s7.prior_pregnancies == "recurrent_miscarriage":
            clinical_flags.append(ClinicalFlag(
                priority=4,
                category="FERTILITY",
                message="Recurrent miscarriage history is present.",
                action="Refer for recurrent pregnancy loss evaluation."
            ))

        if s5.body_image == "severe":
            clinical_flags.append(ClinicalFlag(
                priority=4,
                category="PSYCHOSOCIAL",
                message="Severe body-image distress is present.",
                action="Address psychosocial burden as part of treatment planning."
            ))

        if any(x in s5.psychosexual for x in ["reduced_libido", "body_image_intimacy", "physical_barrier", "multiple"]):
            clinical_flags.append(ClinicalFlag(
                priority=4,
                category="PSYCHOSEXUAL",
                message="Psychosexual concerns are present.",
                action="Offer structured discussion and consider FSFI or specialist referral where appropriate."
            ))

        if composite_score >= 60:
            clinical_flags.append(ClinicalFlag(
                priority=2,
                category="RISK_TIER",
                message="Composite score indicates high overall urgency of assessment.",
                action="Prioritise gynecology / endocrinology review."
            ))
        elif composite_score >= 35:
            clinical_flags.append(ClinicalFlag(
                priority=3,
                category="RISK_TIER",
                message="Composite score indicates moderate overall risk.",
                action="Proceed with full clinical investigation."
            ))

    def _stage8_investigations(
        self,
        data: QuestionnaireSubmitRequest,
        c1_result: str,
        c2_resolution: str,
        c2_signals: List[str],
    ) -> Tuple[List[str], List[Dict[str, str]]]:
        s1 = data.section_1
        s3 = data.section_3
        s4 = data.section_4
        s7 = data.section_7

        recommended: List[str] = [
            "Pelvic ultrasound — TVS preferred with transducer ≥8 MHz; if not acceptable, transabdominal ultrasound. PCOM threshold: FNPO ≥20 or ovarian volume ≥10 mL on either ovary.",
            "Biochemical hyperandrogenism assessment — free testosterone by LC-MS/MS preferred, or total testosterone + SHBG with FAI / calculated free testosterone.",
            "TSH and free T4.",
            "Serum prolactin (fasting if possible).",
            "Fasting lipid profile.",
        ]

        if c1_result == "UNCERTAIN":
            recommended.append("Mid-luteal serum progesterone (day 21 or appropriately timed luteal sample) to confirm ovulation status.")

        if s4.blood_glucose in ["never_tested", "prediabetes", "type2_diabetes"] or s1.bmi >= 23 or "acanthosis_nigricans" in s4.skin_findings or "both" in s4.skin_findings:
            recommended.append("75 g OGTT (preferred baseline metabolic assessment in suspected PCOS).")

        if s4.blood_glucose in ["prediabetes", "type2_diabetes"]:
            recommended.append("HbA1c for glycemic monitoring.")

        if s4.hormonal_status == "elevated_prolactin":
            recommended.append("Pituitary MRI if prolactin remains elevated on confirmatory testing.")

        if s4.hormonal_status in ["cah_diagnosed", "elevated_dheas_androstenedione"]:
            recommended.append("17-hydroxyprogesterone (morning, early follicular phase) to assess for CAH / adrenal differential.")

        if c1_result == "POSITIVE":
            recommended.append("FSH and LH in the early follicular phase if clinically useful.")

        osa_symptom_count = len(
            [x for x in s4.sleep_apnea if x in ["snoring", "waking_unrefreshed", "daytime_sleepiness"]]
        )
        if "diagnosed_osa" in s4.sleep_apnea or osa_symptom_count >= 2:
            recommended.append("Sleep apnea screening with Berlin Questionnaire; sleep specialist referral if screening is positive.")

        if s3.hair_thinning_pattern == "diffuse":
            recommended.append("Ferritin / iron studies if diffuse hair loss is clinically significant.")

        if s7.hormonal_contraception in ["combined_pill", "progestin_only", "hormonal_iud", "stopped_last_3mo"]:
            recommended.append("Delay interpretation of biochemical androgen testing until hormonal contraception washout is adequate.")

        not_recommended = [
            {
                "test": "Serum AMH as a standalone diagnostic test for PCOS",
                "reason": "AMH is not a standalone Rotterdam replacement in this questionnaire-based workflow."
            },
            {
                "test": "Direct free testosterone by routine RIA / ELISA immunoassay",
                "reason": "These assays are unreliable at female testosterone concentrations."
            },
            {
                "test": "Fasting insulin or HOMA-IR as a diagnostic test for PCOS",
                "reason": "They are not validated as diagnostic criteria; OGTT is more clinically useful for metabolic assessment."
            },
        ]

        return self._dedupe_strings(recommended), not_recommended

    def _risk_tier(self, composite_score: int) -> str:
        if composite_score >= 60:
            return "HIGH"
        if composite_score >= 35:
            return "MODERATE"
        return "LOW"

    def _get_ludwig_grade(self, pattern: str) -> int:
        return {
            "mild_crown_ludwig1": 1,
            "moderate_ludwig2": 2,
            "severe_ludwig3": 3,
        }.get(pattern, 0)

    def _dedupe_strings(self, items: List[str]) -> List[str]:
        seen = set()
        output = []
        for item in items:
            if item not in seen:
                seen.add(item)
                output.append(item)
        return output

    def _sort_and_dedupe_flags(self, flags: List[ClinicalFlag]) -> List[ClinicalFlag]:
        seen = set()
        deduped: List[ClinicalFlag] = []
        for flag in sorted(flags, key=lambda x: (x.priority, x.category, x.message)):
            key = (flag.priority, flag.category, flag.message, flag.action)
            if key not in seen:
                seen.add(key)
                deduped.append(flag)
        return deduped