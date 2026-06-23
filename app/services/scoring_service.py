import logging
from typing import Optional, Any
from app.models.enums import TaskId
from app.models.models import TaskAttempt

logger = logging.getLogger(__name__)


def _get_raw_metric(raw: dict, key: str) -> Optional[Any]:
    if not raw:
        return None
    nested = raw.get("rawMetrics")
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    if key in raw:
        return raw[key]
    return None


class ScoringService:
    def calculate_attempt_score(self, attempt: TaskAttempt) -> int:
        """
        Calculate a normalised score (0-100) based on task performance metrics.
        Scoring logic tailored to specific task requirements:
        """
        task_id = attempt.task_id
        
        # Safe default values
        accuracy = float(attempt.accuracy) if attempt.accuracy is not None else 0.0
        correct = attempt.correct_responses or 0
        missed = attempt.missed_responses or 0
        commissions = attempt.commission_errors or 0
        reaction_time = attempt.reaction_time_ms or 0
        
        computed_score = 0

        try:
            if task_id == TaskId.CPT:
                # CPT (Attention): prioritises accuracy (60%), commission errors (20%), and omission errors (20%)
                # Commission penalty: -10 points per commission error (max 100 penalty)
                commission_penalty = min(100, commissions * 10)
                # Omission penalty: -10 points per missed response (max 100 penalty)
                omission_penalty = min(100, missed * 10)
                
                weighted_acc = accuracy * 0.60
                weighted_comm = (100 - commission_penalty) * 0.20
                weighted_omis = (100 - omission_penalty) * 0.20
                
                computed_score = int(weighted_acc + weighted_comm + weighted_omis)

            elif task_id == TaskId.WORD_RECALL:
                # Word Recall (Memory): Percentage of target words recalled
                total_words = correct + missed
                if total_words > 0:
                    computed_score = int((correct / total_words) * 100)
                else:
                    computed_score = int(accuracy)

            elif task_id == TaskId.TOWER_PUZZLE:
                # Tower Puzzle (Reasoning / Executive Planning):
                # Compares moves taken against target optimal moves in config
                raw = attempt.raw_metrics or {}
                optimal_moves = _get_raw_metric(raw, "optimalMoves")
                if optimal_moves is None:
                    optimal_moves = 5
                
                actual_moves = correct  # correct responses represents moves taken in the puzzle
                if actual_moves == 0:
                    computed_score = 0
                else:
                    move_difference = actual_moves - optimal_moves
                    if move_difference <= 0:
                        move_score = 100
                    else:
                        # Deduct 15 points per extra move
                        move_score = max(10, 100 - (move_difference * 15))
                    
                    # Planning time penalty: deduct points if planning/thinking time exceeds 15 seconds
                    time_penalty = 0
                    if reaction_time > 15000:  # > 15 seconds
                        time_penalty = min(20, int((reaction_time - 15000) / 1000))  # max 20 point penalty
                    
                    computed_score = int(move_score - time_penalty)

            elif task_id == TaskId.GO_NO_GO:
                # Go / No-Go (Coordination / Inhibition):
                # Penalty for clicking on No-Go distractors (commission errors)
                commission_penalty = min(100, commissions * 15)
                # Score is 70% accuracy and 30% response inhibition penalty
                computed_score = int((accuracy * 0.70) + ((100 - commission_penalty) * 0.30))

            elif task_id == TaskId.SHAPE_MATCH:
                # Shape Match (Perception / Speed):
                # Accuracy combined with reaction time speed bonus/penalty
                # Base score is accuracy. Add bonus if reaction time is fast (< 1200ms) or penalty if slow (> 2500ms)
                base_score = accuracy
                speed_mod = 0
                if reaction_time > 0:
                    if reaction_time < 1200:
                        speed_mod = 10  # Speed bonus
                    elif reaction_time > 2500:
                        speed_mod = -15  # Slow penalty
                
                computed_score = int(base_score + speed_mod)

            elif task_id == TaskId.DIVIDED_ATTENTION:
                # Divided Attention (Attention): average of primary and secondary accuracy
                # Both are stored in raw_metrics; fall back to overall accuracy if absent.
                raw = attempt.raw_metrics or {}
                primary_val = _get_raw_metric(raw, "primaryAccuracy")
                secondary_val = _get_raw_metric(raw, "secondaryAccuracy")
                primary = float(primary_val) if primary_val is not None else accuracy
                secondary = float(secondary_val) if secondary_val is not None else accuracy
                computed_score = int((primary + secondary) / 2)

            elif task_id == TaskId.UPDATING:
                # Updating (Memory): accuracy weighted by highest difficulty level reached.
                # Higher N-Back levels are rewarded with a multiplier (cap at 100).
                raw   = attempt.raw_metrics or {}
                level_val = _get_raw_metric(raw, "difficultyLevel")
                level = int(level_val) if level_val is not None else 1
                computed_score = min(100, int(accuracy * (0.7 + level * 0.1)))

            elif task_id == TaskId.N_BACK:
                # N-Back (Working Memory): direct accuracy
                computed_score = int(accuracy)

            else:
                # Fallback to direct accuracy
                computed_score = int(accuracy)

        except Exception as e:
            logger.error(f"Scoring error on task '{task_id}': {e}")
            computed_score = int(accuracy)

        # Enforce range [0, 100]
        return max(0, min(100, computed_score))


scoring_service = ScoringService()
