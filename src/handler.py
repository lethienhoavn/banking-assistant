import traceback
import sys
import json
import re

from botbuilder.core import TurnContext, BotFrameworkAdapterSettings, BotFrameworkAdapter, ActivityHandler, MessageFactory
from botbuilder.schema import Attachment, Activity, ActivityTypes, CardImage, HeroCard

from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.agents import OpenAIFunctionsAgent, AgentExecutor
from langchain.schema import SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate

from config import Config

from llm_config.system_instruct import SYSTEM_MESSAGE

from tools.sql import run_query_tool, describe_tables_tool
from tools.report import write_report_tool
from tools.chart import plot_chart_tool
from tools.analysis import (
    calculate_clv_tool,
    survival_analysis_tool,
    churn_classification_tool,
    uplift_modeling_tool,
    discover_churn_factors_tool
)



### 1. Initial loading ====================

# Load LLM config file
with open("llm_config/config.json", "r", encoding="utf-8") as f:
    llm_config = json.load(f)

completion_cfg = llm_config.get("completion", {})
llm_params = {
    "temperature": completion_cfg.get("temperature", 0)
}



### 2. Agent setup ====================
llm = ChatOpenAI(
    openai_api_key=Config.OPENAI_API_KEY,
    model_name=Config.OPENAI_MODEL_NAME,
    **llm_params
)

# Prompt template
chat_prompt = ChatPromptTemplate(
    messages=[
        SystemMessage(content=SYSTEM_MESSAGE),
        MessagesPlaceholder(variable_name="chat_history"),
        HumanMessagePromptTemplate.from_template("{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ]
)

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

tools = [
    run_query_tool,
    describe_tables_tool,
    write_report_tool,
    plot_chart_tool,
    calculate_clv_tool,
    survival_analysis_tool,
    churn_classification_tool,
    uplift_modeling_tool,
    discover_churn_factors_tool
]

agent = OpenAIFunctionsAgent(
    llm=llm,
    prompt=chat_prompt,
    tools=tools
)

agent_executor = AgentExecutor(
    agent=agent,
    verbose=True,
    tools=tools,
    memory=memory
)



### 3. Bot Execution ====================

def extract_image_path(text: str):
    match = re.search(r"(charts/[a-zA-Z0-9_\-]+\.png)", text)
    return match.group(1) if match else None


def extract_ngrok_url_from_log(log_path="ngrok_logs/ngrok.log", encoding="utf-8", errors="ignore"):
    with open(log_path, "r", encoding=encoding, errors=errors) as f:
        lines = f.readlines()

    for line in lines:
        clean_line = line.replace('\x00', '').strip()
        match = re.search(r"url=(https://[a-zA-Z0-9\-]+\.ngrok-free.app)", clean_line)
        if match:
            return match.group(1)

    raise ValueError("No ngrok public URL found in log.")
    

class LangChainBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        user_id = turn_context.activity.from_property.id
        user_input = turn_context.activity.text

        conversation = agent_executor(user_input)
        response = conversation['output']

        if isinstance(response, str):
            image_path = extract_image_path(response)
            # print("image_path: ", image_path, flush=True)

            if image_path:
                try:
                    url = extract_ngrok_url_from_log("ngrok_logs/ngrok.log")
                    print(f"✅ Found ngrok URL: {url}", flush=True)

                    image_url = f"{url}/{image_path}"
                    print("image_url: ", image_url)

                    card = HeroCard(
                        images=[CardImage(url=image_url)]
                    )
                    attachment = Attachment(
                        content_type="application/vnd.microsoft.card.hero",
                        content=card
                    )
                    await turn_context.send_activity(
                        Activity(type=ActivityTypes.message, attachments=[attachment])
                    )
                except Exception as e:
                    print(f"❌ Error: {e}")
                    await turn_context.send_activity(MessageFactory.text("Error generating plots !"))
            else:
                await turn_context.send_activity(MessageFactory.text(response))
        else:
            await turn_context.send_activity(MessageFactory.text(str(response)))




### 4. Adapter settings ====================
adapter_settings = BotFrameworkAdapterSettings(
    app_id=Config.APP_ID,
    app_password=Config.APP_PASSWORD,
)
adapter = BotFrameworkAdapter(adapter_settings)

bot_app = LangChainBot()



### 5. Handling bot error ====================
async def on_error(turn_context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await turn_context.send_activity("The bot encountered an error or bug.")

adapter.on_turn_error = on_error