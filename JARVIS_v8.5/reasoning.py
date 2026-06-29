class ReasoningEngine:
    def __init__(self):
        self.last_topic = None

    def analyze(self, user_input, memory_hits=None):
        result = {
            "intent": None,
            "missing_info": [],
            "plan": [],
            "confidence": 1.0
        }

        text = user_input.lower()

        if "yap" in text:
            result["intent"] = "task"

        elif "nedir" in text:
            result["intent"] = "question"

        else:
            result["intent"] = "conversation"

        if len(text.split()) < 2:
            result["confidence"] = 0.3
            result["missing_info"].append(
                "Daha fazla detay gerekli."
            )

        if result["intent"] == "task":
            result["plan"] = [
                "isteği_anla",
                "bilgileri_topla",
                "çözüm_oluştur"
            ]

        return result