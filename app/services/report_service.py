import logging
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.models import (
    Report,
    AssessmentSession,
    Patient,
    Doctor,
    QuestionnaireResponse,
    PatientScoreHistory,
    AuditLog,
    TaskAttempt,
)
from app.models.enums import SessionStatus, AuditActorType, AuditAction, QuestionnaireSlug
from app.repositories.report import report_repo
from app.repositories.patient import patient_repo

logger = logging.getLogger(__name__)


def _get_raw_metric(raw: dict, key: str) -> Optional[Any]:
    if not raw:
        return None
    if key in raw:
        return raw[key]
    nested = raw.get("rawMetrics")
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return None


class ReportService:
    async def generate_report(
        self, db: AsyncSession, *, session_id: UUID, ip_address: Optional[str] = None
    ) -> Report:
        """Calculate score metrics and generate the clinical report snapshot for a completed session."""
        # 1. Retrieve session and check status is completed
        stmt = (
            select(AssessmentSession)
            .filter(AssessmentSession.id == session_id)
            .options(
                selectinload(AssessmentSession.steps),
                selectinload(AssessmentSession.attempts),
            )
        )
        session = (await db.execute(stmt)).scalars().first()
        if not session:
            raise NotFoundException("Assessment session not found")

        # [Critical Issue #4] Verify status is completed
        if session.status != SessionStatus.COMPLETED:
            raise BadRequestException(
                f"Cannot generate report: session {session_id} has status '{session.status}' "
                f"(must be 'completed')."
            )

        # Check if report already exists for this session to prevent duplicate runs
        existing_report = await report_repo.get_by_session_id(db, session_id=session_id)
        if existing_report:
            return existing_report

        # 2. Fetch Patient and Doctor metadata
        patient = await patient_repo.get(db, session.patient_id)
        if not patient:
            raise NotFoundException("Patient not found")

        doctor_stmt = select(Doctor).filter(Doctor.id == session.doctor_id)
        doctor = (await db.execute(doctor_stmt)).scalars().first()
        if not doctor:
            raise NotFoundException("Clinician not found")

        # 3. Retrieve questionnaire responses
        q_stmt = select(QuestionnaireResponse).filter(QuestionnaireResponse.session_id == session_id)
        q_responses = list((await db.execute(q_stmt)).scalars().all())
        
        phq9_val: Optional[int] = None
        gad7_val: Optional[int] = None
        pss10_val: Optional[int] = None
        araq_val: Optional[int] = None
        araq_sec_a_val: Optional[int] = None
        araq_sec_b_val: Optional[int] = None
        araq_sec_c_val: Optional[int] = None
        araq_sec_d_val: Optional[int] = None

        for qr in q_responses:
            if qr.slug == QuestionnaireSlug.PHQ_9:
                phq9_val = qr.total_score
            elif qr.slug == QuestionnaireSlug.GAD_7:
                gad7_val = qr.total_score
            elif qr.slug == QuestionnaireSlug.PSS_10:
                pss10_val = qr.total_score
            elif qr.slug == QuestionnaireSlug.ARAQ:
                araq_val = qr.total_score
                answers = qr.answers or {}
                # Calculate sub-section scores: Section A (1-8), Section B (9-14), Section C (15-22), Section D (23-26)
                # Note: items are stored with keys q1 to q26
                araq_sec_a_val = sum(int(answers.get(f"q{i}", 0)) for i in range(1, 9))
                araq_sec_b_val = sum(int(answers.get(f"q{i}", 0)) for i in range(9, 15))
                araq_sec_c_val = sum(int(answers.get(f"q{i}", 0)) for i in range(15, 23))
                araq_sec_d_val = sum(int(answers.get(f"q{i}", 0)) for i in range(23, 27))

        # 4. Calculate domain scores (average computed_score of real attempts per domain)
        domain_scores = {
            "Attention": [],
            "Memory": [],
            "Reasoning": [],
            "Coordination": [],
            "Perception": [],
        }

        # Retrieve all task attempts for this session fresh from DB to avoid identity-map caching issues
        attempts_stmt = select(TaskAttempt).filter(TaskAttempt.session_id == session_id)
        attempts = list((await db.execute(attempts_stmt)).scalars().all())
        if not attempts and session.attempts:
            attempts = session.attempts
        real_attempts = [a for a in attempts if not a.is_practice]
        for att in real_attempts:
            domain_name = att.domain
            if domain_name in domain_scores and att.computed_score is not None:
                domain_scores[domain_name].append(att.computed_score)

        # Average helper
        def avg_score(scores_list: List[int]) -> Optional[int]:
            if not scores_list:
                return None
            return int(sum(scores_list) / len(scores_list))

        score_attention    = avg_score(domain_scores["Attention"])
        score_memory        = avg_score(domain_scores["Memory"])
        score_reasoning     = avg_score(domain_scores["Reasoning"])
        score_coordination  = avg_score(domain_scores["Coordination"])
        score_perception    = avg_score(domain_scores["Perception"])

        # Overall total score is average of all real attempts (or fallback to 0)
        all_computed_scores = [att.computed_score for att in real_attempts if att.computed_score is not None]
        total_score = int(sum(all_computed_scores) / len(all_computed_scores)) if all_computed_scores else 0

        # 4b. Extract domain-specific clinical metrics from rawMetrics for enhanced recommendations
        clinical_metrics: dict = {}
        for att in real_attempts:
            raw  = att.raw_metrics or {}
            task = att.task_id.value if hasattr(att.task_id, "value") else str(att.task_id)
            if task.startswith("TaskId."):
                task = task.split(".")[1].lower().replace("_", "-")
            
            v_drop = _get_raw_metric(raw, "vigilanceDrop")
            if task == "cpt" and v_drop is not None:
                clinical_metrics["vigilanceDrop"] = float(v_drop)
                
            i_control = _get_raw_metric(raw, "inhibitoryControlIndex")
            if task == "go-no-go" and i_control is not None:
                clinical_metrics["inhibitoryControlIndex"] = float(i_control)
                
            r_score = _get_raw_metric(raw, "retentionScore")
            if task == "word-recall" and r_score is not None:
                clinical_metrics["retentionScore"] = float(r_score)
                
            eff_score = _get_raw_metric(raw, "efficiencyScore")
            if task == "tower-puzzle" and eff_score is not None:
                clinical_metrics["efficiencyScore"] = float(eff_score)
                
            i_score = _get_raw_metric(raw, "interferenceScore")
            if task == "divided-attention" and i_score is not None:
                clinical_metrics["interferenceScore"] = float(i_score)
                
            u_eff = _get_raw_metric(raw, "updatingEfficiency")
            if task == "updating" and u_eff is not None:
                clinical_metrics["updatingEfficiency"] = float(u_eff)

        # 5. Formulate clinical recommendations based on thresholds
        recommendations = []
        if score_memory is not None and score_memory < 50:
            recommendations.append(
                "Engage in memory training exercises (e.g. daily word puzzles, associations) to strengthen temporal lobe recall."
            )
        if score_attention is not None and score_attention < 50:
            recommendations.append(
                "Incorporate focused attention tasks and mindfulness exercises to mitigate omission errors and distractions."
            )
        if score_reasoning is not None and score_reasoning < 50:
            recommendations.append(
                "Employ cognitive pacing techniques and step-by-step logic checklists during reasoning and planning tasks."
            )
        if score_coordination is not None and score_coordination < 50:
            recommendations.append(
                "Review coordination and motor pacing activities. Consult physical therapist if functional mobility is impacted."
            )
        if phq9_val is not None and phq9_val >= 10:
            recommendations.append(
                "Moderate-to-severe depressive symptoms indicated. Recommend clinical neuropsychological review or counseling consult."
            )
        if gad7_val is not None and gad7_val >= 10:
            recommendations.append(
                "Moderate-to-severe anxiety symptoms reported. Consider stress reduction therapy and anxiety monitoring."
            )
        if araq_sec_a_val is not None and araq_sec_a_val >= 20:
            recommendations.append(
                "High ADHD-type Executive Dysfunction reported. Suggest clinical assessment for attention-deficit traits."
            )
        if araq_sec_d_val is not None and araq_sec_d_val >= 9:
            recommendations.append(
                "Significant functional impairment/avoidance impact detected. Recommend cognitive behavioral coaching for procrastination."
            )

        # 5b. Clinical metric-specific recommendations
        if clinical_metrics.get("vigilanceDrop", 0) < -20:
            recommendations.append(
                "Significant vigilance decline detected across sustained attention trials (vigilanceDrop < -20%). "
                "Consider evaluation for attentional fatigue, sleep quality, and sustained attention training protocols."
            )
        if clinical_metrics.get("inhibitoryControlIndex", 1.0) < 0.6:
            recommendations.append(
                "Impaired inhibitory control index detected (ICI < 0.60). "
                "Impulse regulation therapy and Go/No-Go specific inhibition training may be clinically beneficial."
            )
        if clinical_metrics.get("retentionScore", 1.0) < 0.5:
            recommendations.append(
                "Poor verbal retention at high memory load (Level 3 retention < 50%). "
                "Structured verbal memory strategy training (e.g. chunking, spaced repetition) is recommended."
            )
        if clinical_metrics.get("efficiencyScore", 1.0) < 0.6:
            recommendations.append(
                "Executive planning efficiency is below optimal threshold (efficiency < 0.60). "
                "Step-by-step planning exercises and frontal lobe activation strategies are suggested."
            )
        if clinical_metrics.get("interferenceScore", 0) > 30:
            recommendations.append(
                "High dual-task interference detected (interferenceScore > 30). "
                "Divided attention rehabilitation exercises may help reduce cognitive load under multi-task conditions."
            )
        if clinical_metrics.get("updatingEfficiency", 1.0) < 0.6:
            recommendations.append(
                "Reduced updating efficiency detected (efficiency < 60%). "
                "Difficulties may exist in monitoring and updating working-memory contents."
            )

        # 5c. Compile full clinical metrics for storage
        compiled_clinical_metrics = {}
        for att in real_attempts:
            task = att.task_id.value if hasattr(att.task_id, "value") else str(att.task_id)
            if task.startswith("TaskId."):
                task = task.split(".")[1].lower().replace("_", "-")
            raw = att.raw_metrics or {}
            
            task_data = {
                "accuracy": int(att.accuracy) if att.accuracy is not None else 0,
                "reactionTime": att.reaction_time_ms or 0,
                "correctResponses": att.correct_responses,
                "missedResponses": att.missed_responses,
                "commissionErrors": att.commission_errors,
            }
            
            if task == "cpt":
                v_drop = _get_raw_metric(raw, "vigilanceDrop")
                if v_drop is not None:
                    task_data["vigilanceDrop"] = float(v_drop)
            elif task == "go-no-go":
                i_control = _get_raw_metric(raw, "inhibitoryControlIndex")
                if i_control is not None:
                    task_data["inhibitoryControlIndex"] = float(i_control)
            elif task == "word-recall":
                r_score = _get_raw_metric(raw, "retentionScore")
                if r_score is not None:
                    task_data["retentionScore"] = float(r_score)
                i_errors = _get_raw_metric(raw, "intrusionErrors")
                if i_errors is not None:
                    task_data["intrusionErrors"] = int(i_errors)
            elif task == "n-back":
                nb_level = _get_raw_metric(raw, "nBackLevel")
                if nb_level is not None:
                    task_data["nBackLevel"] = int(nb_level)
            elif task == "updating":
                u_eff = _get_raw_metric(raw, "updatingEfficiency")
                if u_eff is not None:
                    task_data["updatingEfficiency"] = float(u_eff)
            elif task == "tower-puzzle":
                eff_score = _get_raw_metric(raw, "efficiencyScore")
                if eff_score is not None:
                    task_data["efficiencyScore"] = float(eff_score)
                p_time = _get_raw_metric(raw, "planningTimeMs")
                if p_time is not None:
                    task_data["planningTimeMs"] = float(p_time)
            elif task == "divided-attention":
                p_acc = _get_raw_metric(raw, "primaryAccuracy")
                if p_acc is not None:
                    task_data["primaryAccuracy"] = float(p_acc)
                s_acc = _get_raw_metric(raw, "secondaryAccuracy")
                if s_acc is not None:
                    task_data["secondaryAccuracy"] = float(s_acc)
                i_score = _get_raw_metric(raw, "interferenceScore")
                if i_score is not None:
                    task_data["interferenceScore"] = float(i_score)
                    
            compiled_clinical_metrics[task] = task_data

        # Standard baseline recommendations if none added
        if not recommendations:
            recommendations.append("Continue current cognitive wellness baseline activities.")
            recommendations.append("Schedule standard re-assessment in 6 to 12 months to monitor long-term stability.")

        # 6. Generate human-readable report reference ID (e.g. CAP-2026-XXXX)
        current_year = datetime.now().year
        rand_hex = secrets.token_hex(2).upper()
        report_ref_id = f"CAP-{current_year}-{rand_hex}"

        # 7. Construct Report
        db_report = Report(
            report_id=report_ref_id,
            medical_id_snapshot=patient.medical_id,
            session_id=session_id,
            patient_id=session.patient_id,
            doctor_id=session.doctor_id,
            patient_name=patient.name,
            patient_age=patient.age,
            patient_gender=patient.gender,
            patient_phone=patient.phone,
            clinician_name=doctor.name,
            total_score=total_score,
            # score_status is left blank/omitted in inserts as it is generated in PostgreSQL
            score_attention=score_attention,
            score_memory=score_memory,
            score_reasoning=score_reasoning,
            score_coordination=score_coordination,
            score_perception=score_perception,
            phq9_score=phq9_val,
            gad7_score=gad7_val,
            pss10_score=pss10_val,
            araq_score=araq_val,
            araq_sec_a_score=araq_sec_a_val,
            araq_sec_b_score=araq_sec_b_val,
            araq_sec_c_score=araq_sec_c_val,
            araq_sec_d_score=araq_sec_d_val,
            recommendations=recommendations,
            system_version="2.5.0-LTS",
            language=session.language,
            is_archived=False,
            clinical_metrics=compiled_clinical_metrics,
        )
        db.add(db_report)
        await db.flush()
        
        # Reload to get derived score_status from the database trigger/computed column
        await db.refresh(db_report)
        
        session.report = db_report

        # 8. Create PatientScoreHistory entry linked to report (trigger enforces score equality)
        date_label = datetime.now().strftime("%b %d")
        score_history = PatientScoreHistory(
            patient_id=session.patient_id,
            report_id=db_report.id,
            score=total_score,
            attention_score=score_attention,
            memory_score=score_memory,
            reasoning_score=score_reasoning,
            coordination_score=score_coordination,
            perception_score=score_perception,
            label=date_label,
            assessed_on=datetime.now(timezone.utc).date(),
        )
        db.add(score_history)

        # 9. Audit log report generation
        audit = AuditLog(
            actor_id=session.doctor_id,
            actor_type=AuditActorType.DOCTOR,
            action=AuditAction.REPORT_GENERATE,
            entity_type="report",
            entity_id=db_report.id,
            metadata_={"report_ref": report_ref_id, "overall_score": total_score},
            ip_address=ip_address,
        )
        db.add(audit)
        await db.flush()

        return db_report


report_service = ReportService()
