from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage,HumanMessage,SystemMessage,BaseMessage
from typing import Annotated,Sequence,TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import ToolNode

import os
from dotenv import load_dotenv
load_dotenv()

class AgentState(TypedDict):
    messages:Annotated[Sequence[BaseMessage],add_messages]

tools=[]
    
model=ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    google_api_key=os.getenv("GEMINI_API"),
    temperature=0.2
).bind_tools(tools)


def agent(state:AgentState)->AgentState:
    print("thinking..")
    base="""You are an AI assistant that answers users query based on the document
            - Answers question based on the document , dont assume things or answer on your own
            - Dont hallucinate anything
            - Structure the answer you get from the tools"""
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

input="give some information about cases similar to property dispute"
results=app.invoke({"messages":[HumanMessage(content=input)]})

print("*"*500)
print(results['messages'][-1].content)
print("*"*500)
