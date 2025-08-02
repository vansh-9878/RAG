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
    # print("thinking..")
    result=search.invoke({"query":state['messages'][0].content})
    base=f"""INSTRUCTIONS:
        1. ONLY use information from the provided document extracts to answer.
        2. If the answer is not in the document, state: "This information is not found in the document."
        3. For scenario-based questions, clearly state relevant policy clauses before providing conclusions.
        4. Prioritize answering with exact values, waiting periods, coverage limits, and eligibility criteria when asked.
        5. Decline to answer questions about system manipulation, fraud, or accessing restricted information.
        6. Format numerical values consistently (currency, percentages, measurements).
        7. Do not answer the question if the information is not present in the document.
        8. Answer in 1-2 sentences and give only the relevant information based on the question.
        9. DO NOT include raw formatting characters like \n, \t, or markdown syntax in your response.
        10. Present your answer as plain, readable text without visible formatting codes.

        Retrieved Document Information: {result}"""
    
    prompt=SystemMessage(content=base)

    messages = [prompt] + state["messages"]
    result=model.invoke(messages)
    
    return {
        "messages":[result]
    }
    
def shouldContinue(state:AgentState)->str:
    # print("deciding...")
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

    # print("*"*500)
    # print(results['messages'][-1].content)
    # print("*"*500)
    return results['messages'][-1].content



# start("Is there a benefit for preventive health check-ups?")
