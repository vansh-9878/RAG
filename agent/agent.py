from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage,HumanMessage,SystemMessage,BaseMessage
from typing import Annotated,Sequence,TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import ToolNode
from search import searchDocument

import os
from dotenv import load_dotenv
load_dotenv()

class AgentState(TypedDict):
    messages:Annotated[Sequence[BaseMessage],add_messages]
    filename:str

tools=[searchDocument]
    
model=ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    google_api_key=os.getenv("GEMINI_API"),
    temperature=0.2
).bind_tools(tools)


def agent(state:AgentState)->AgentState:
    print("thinking..")
    base=f"""You are an AI assistant that answers questions strictly based on retrieved documents.
        - Always use the `searchDocument` tool to retrieve information.
        - `searchDocument` takes two arguments:
            - query: the user's question
            - filename: the name of the document
        - Do not answer unless you've retrieved information using the tool.
        - If the document doesn't contain the answer, say: "The document does not contain this information."
        - Do not guess or use outside knowledge.
        - File name : {state['filename']}"""
    prompt=SystemMessage(content=base)

    messages = [prompt] + state["messages"]
    result=model.invoke(messages)
    
    return {
        "messages":[result]
    }
    
def shouldContinue(state:AgentState)->str:
    print("deciding...")
    lastMessage=state["messages"][-1]
    if(lastMessage.tool_calls):
        return "continue"
    else:
        return "end"
    
graph=StateGraph(AgentState)
graph.add_node("agent",agent)
graph.add_node("tools",ToolNode(tools))
graph.add_edge(START,"agent")
graph.add_edge("tools","agent")
graph.add_conditional_edges(
    "agent",
    shouldContinue,
    {
        "continue":"tools",
        "end":END
    }
)

app=graph.compile()

input="what is the grace period for renewing the policy"
results=app.invoke({"messages":[HumanMessage(content=input)],"filename":"travel_insurance"})

print("*"*500)
print(results['messages'][-1].content)
print("*"*500)
