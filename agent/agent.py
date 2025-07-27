from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage,HumanMessage,SystemMessage,BaseMessage,ToolMessage
from typing import Annotated,Sequence,TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph,START,END
from agent.localDatabase import search
# from localDatabase import search
import os
from dotenv import load_dotenv
load_dotenv()

class AgentState(TypedDict):
    messages:Annotated[Sequence[BaseMessage],add_messages]

# tools=[search]
    
model=ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API"),
    temperature=0.2
)


def agent(state:AgentState)->AgentState:
    print("thinking..")
    result=search.invoke({"query":state['messages'][0].content})
    base=f"""You are an AI assistant that answers questions strictly based on retrieved documents.
        - You are given retrieved information at the bottom use that to answer the query
        - If the document doesn't contain the answer, say: "The document does not contain this information."
        - Do not guess or use outside knowledge.
        - Give the response in 2-3 lines only important information related to the query
        - Retrieved Information : {result}"""
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
# graph.add_node("tools",ToolNode(tools))
graph.add_edge(START,"agent")
# graph.add_edge("tools","agent")
# graph.add_conditional_edges(
#     "agent",
#     shouldContinue,
#     {
#         "continue":"tools",
#         "end":END
#     }
# )
graph.add_edge("agent",END)

app=graph.compile()

def start(input:str)->str:
    # input="what is the grace period for renewing the policy"
    results=app.invoke({"messages":[HumanMessage(content=input)]})

    print("*"*500)
    print(results['messages'][-1].content)
    print("*"*500)
    return results['messages'][-1].content

# start("Is there a benefit for preventive health check-ups?")