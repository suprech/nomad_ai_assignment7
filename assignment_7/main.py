import asyncio

import dotenv
import streamlit as st
from openai import OpenAI
from agents import Agent, Runner, SQLiteSession, WebSearchTool

dotenv.load_dotenv()

client = OpenAI()

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="Life Coach",
        instructions="""
        You are a warm, encouraging life coach who helps users build better habits, stay motivated, and grow personally.

        Guidelines:
        - Always respond in the same language the user uses.
        - Be empathetic, positive, and action-oriented.
        - Give practical, specific advice rather than vague encouragement.
        - When the user asks about habits, motivation, self-improvement, or personal challenges, use the Web Search Tool to find evidence-based tips and latest research.
        - Structure your advice with clear, numbered steps when appropriate.
        - Celebrate the user's small wins and progress.
        - End responses with an encouraging message or a follow-up question to keep the conversation going.

        You have access to the following tools:
        - Web Search Tool: Use this to search for motivational content, self-development tips, habit formation advice, and evidence-based strategies.
        """,
        tools=[
            WebSearchTool(),
        ],
    )

agent = st.session_state["agent"]

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history",
        "chat-gpt-clone-memory.db",
    )

session = st.session_state["session"]


async def paint_history():
    messages = await session.get_items()

    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\$"))

        if "type" in message:
            if message["type"] == "web_search_call":
                with st.chat_message("ai"):
                    st.write("🔍 Searched the web...")
            elif message["type"] == "file_search_call":
                with st.chat_message("ai"):
                    st.write("🗂️ Searched your files...")


def update_status(status_container, event):

    status_messages = {
        "response.web_search_call.completed": ("✅ Web search completed.", "complete"),
        "response.web_search_call.in_progress": (
            "🔍 Starting web search...",
            "running",
        ),
        "response.web_search_call.searching": (
            "🔍 Web search in progress...",
            "running",
        ),
    }
    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)


async def run_agent(message):
    with st.chat_message("ai"):
        status_container = st.status("⏳", expanded=False)
        text_placeholder = st.empty()
        response = ""

        stream = Runner.run_streamed(agent, message, session=session)

        async for event in stream.stream_events():
            if event.type == "raw_response_event":

                update_status(status_container, event.data.type)

                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response.replace("$", "\$"))


asyncio.run(paint_history())

prompt = st.chat_input("Write a message for your assistant")

if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    asyncio.run(run_agent(prompt))


with st.sidebar:
    reset = st.button("reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))
