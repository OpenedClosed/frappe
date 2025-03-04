
"""База знаний бота с переводами."""
from chats.db.mongo.schemas import BriefQuestion

BRIEF_QUESTIONS = [

    # BriefQuestion(
    #     question="Hello! Welcome to Friendly Assistant. 😊\n\nHow can we assist you today?",
    #     question_translations={
    #         "en": "Hello! Welcome to Friendly Assistant. 😊\n\nHow can we assist you today?",
    #         "ru": "Здравствуйте! Добро пожаловать в Friendly Assistant. 😊\n\nКак мы можем вам помочь?",
    #         "ar": "مرحبًا! أهلاً بك في Friendly Assistant. 😊\n\nكيف يمكننا مساعدتك اليوم؟"
    #     },
    #     question_type="text",
    #     expected_answers=[],
    #     expected_answers_translations={
    #         "en": [],
    #         "ru": [],
    #         "ar": []
    #     }
    # ),
]



KNOWLEDGE_BASE = {
    "Topic": {
        "subtopics": {
            "subtopic": {
                "questions": {
                    "question?": {
                        "text": "text",
                        "images": []
                    }
                }
            }
        }
    }
}
