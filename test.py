from flask import Flask, request, jsonify
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import dotenv
from flask_cors import CORS

dotenv.load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
                As an experienced medical professional, you are tasked with conducting a thorough patient consultation.

                    Instructions:
                    First: Begin by gathering essential information from the patient, including their name, age, and location.
                    Second: Ask the patient how they are currently feeling. For instance, inquire about any symptoms they may be experiencing, such as fever, pain, fatigue, etc.
                    Third: If the patient mentions any specific symptoms (e.g., fever), proceed with follow-up questions to gather more detailed information. For example, ask about the duration, severity, and any other accompanying symptoms like headaches, body aches, or chills.
                    Fourth: Continue asking clarifying questions about the patient’s symptoms, medical history, recent activities, or potential exposure to illnesses, to better understand the nature of their condition.
                    Finally: Your goal is to narrow down the possible diagnosis or conditions based on the information provided by the patient.
                    Be precise and empathetic in your approach, ensuring that the patient feels heard and supported throughout the consultation.
                """,
        ),
        ("placeholder", "{chat_history}"),
        ("user", "{input}"),
    ]
)

demo_ephemeral_chat_history = ChatMessageHistory()

chain = prompt | llm

chain_with_message_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: demo_ephemeral_chat_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)


def chat_bot(input):
    response = chain_with_message_history.invoke(
        {"input": input},
        {"configurable": {"session_id": "unused"}},
    )
    return response.content


@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    data = request.json
    input_text = data.get("input_text")
    return jsonify({"response": chat_bot(input_text)})


if __name__ == "__main__":
    app.run(debug=True)
