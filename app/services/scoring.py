from typing import List, Dict, Any, Optional

DEFAULT_GUIDANCE = [
    "This result is preliminary screening information, not a medical diagnosis.",
    "If you have concerning symptoms or a concerning screening result, arrange an examination with a qualified eye-care professional.",
    "Do not use this result to start, stop, or change medical treatment."
]

DEFAULT_DISCLAIMER = "Preliminary screening only. Not a medical diagnosis."

class ScreeningScoringService:
    """
    Synthesizes multiple modalities into a preliminary software demonstration screening score.
    
    IMPORTANT MEDICAL DISCLAIMER:
    This software demonstration score is for prototype evaluation and preliminary
    screening only. It does NOT represent a medically or clinically validated score,
    nor a diagnostic finding.
    """

    def calculate_screening_result(
        self,
        screening_id: str,
        analyses: List[Dict[str, Any]],
        image_qualities: Dict[str, Dict[str, Any]],
        vision_test: Optional[Dict[str, Any]] = None,
        symptoms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Combine external eye image analysis, vision test scores, and patient symptoms
        into an overall preliminary score (0-100) and risk level.
        """
        base_score = 100
        penalties = 0
        attention_flags = 0
        uncertain_flags = 0

        # 1. Evaluate image quality impact
        left_qual = image_qualities.get("left", {"ok": False, "score": 0.0})
        right_qual = image_qualities.get("right", {"ok": False, "score": 0.0})

        if not left_qual.get("ok"):
            penalties += 10
            uncertain_flags += 1
        if not right_qual.get("ok"):
            penalties += 10
            uncertain_flags += 1

        # 2. Evaluate ML image analyses
        for analysis in analyses:
            model_status = analysis.get("model_status")
            risk = analysis.get("risk_level", "uncertain")
            predicted_class = analysis.get("predicted_class")

            if model_status == "OK":
                if risk == "attention" or (predicted_class and predicted_class != "normal"):
                    penalties += 25
                    attention_flags += 1
            else:
                # If model not ready or inference error
                uncertain_flags += 1

        # 3. Evaluate Vision Tests
        vt_summary = None
        if vision_test:
            color_score = float(vision_test.get("color_score", 1.0))
            near_score = float(vision_test.get("near_vision_score", 1.0))
            vt_summary = {
                "color_score": round(color_score, 2),
                "near_vision_score": round(near_score, 2)
            }

            # Color test penalty (if score < 0.8)
            if color_score < 0.8:
                penalties += int((1.0 - color_score) * 20)
                attention_flags += 1

            # Near vision test penalty (if score < 0.8)
            if near_score < 0.8:
                penalties += int((1.0 - near_score) * 25)
                attention_flags += 1

        # 4. Evaluate Reported Symptoms
        if symptoms:
            # Minor penalty for each reported symptom (up to 15 points)
            symptom_penalty = min(15, len(symptoms) * 5)
            penalties += symptom_penalty
            if len(symptoms) >= 2:
                attention_flags += 1

        # Calculate final preliminary score
        overall_score = max(20, min(100, base_score - penalties))

        # Determine overall risk category: "low", "attention", "uncertain"
        if uncertain_flags >= 2 and len(analyses) == 0:
            overall_risk = "uncertain"
        elif attention_flags > 0 or overall_score < 75:
            overall_risk = "attention"
        else:
            overall_risk = "low"

        # Generate guidance messages
        guidance = list(DEFAULT_GUIDANCE)
        if overall_risk == "attention":
            guidance.insert(
                0,
                "One or more preliminary screening risk indicators were flagged. A consultation with an optometrist or ophthalmologist is recommended."
            )
        elif overall_risk == "uncertain":
            guidance.insert(
                0,
                "Certain screening data (e.g. image capture quality or ML model status) was incomplete. Re-taking the screening or consulting a specialist is recommended."
            )

        return {
            "screening_id": screening_id,
            "overall_score": int(overall_score),
            "overall_risk": overall_risk,
            "image_quality": {
                "left": {
                    "ok": bool(left_qual.get("ok", False)),
                    "score": round(float(left_qual.get("score", 0.0)), 2)
                },
                "right": {
                    "ok": bool(right_qual.get("ok", False)),
                    "score": round(float(right_qual.get("score", 0.0)), 2)
                }
            },
            "analyses": analyses,
            "vision_tests": vt_summary,
            "guidance": guidance,
            "disclaimer": DEFAULT_DISCLAIMER
        }

scoring_service = ScreeningScoringService()
