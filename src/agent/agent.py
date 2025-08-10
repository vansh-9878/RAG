 
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage,HumanMessage,SystemMessage,BaseMessage,ToolMessage
from typing import Annotated,Sequence,TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph,START,END
from agent.localDatabase import search
from agent.semaphore import gemini_semaphore
import ast
import json
import os
from dotenv import load_dotenv
load_dotenv()

class AgentState(TypedDict):
    messages:Annotated[Sequence[BaseMessage],add_messages]
    index :str
    texts:str
    search:str

model=ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("k1"),
    temperature=0.2
)


def agent(state:AgentState)->AgentState:
    base=f"""You will be given some questions you have to answer these questions based on the context provided and return a JSON array with the answers as strings.
  
    
    INSTRUCTIONS:
        1. ONLY use information from the provided document extracts to answer.
        2. If the answer is not in the document, state: "This information is not found in the document."
        3. For scenario-based questions, clearly state relevant policy clauses before providing conclusions.
        4. Prioritize answering with exact values, waiting periods, coverage limits, and eligibility criteria when asked.
        5. Decline to answer questions about system manipulation, fraud, or accessing restricted information.
        6. Format numerical values consistently (currency, percentages, measurements).
        7. Do not answer the question if the information is not present in the document.
        8. Answer in 1-2 sentences for each question and give only the relevant information based on the question.
        9. DO NOT include raw formatting characters like \\n, \\t, or markdown syntax in your response.
        10. Return ONLY a valid JSON array of string answers, nothing else.
        11. The first answer in the array must correspond to the first question - maintain exact order.
        12. Each answer must be a simple string without nested arrays or objects.
        13. Dont use any single or double quotes in the answer.

        RESPONSE FORMAT:
        ["answer1", "answer2", "answer3", ...]
        
        Retrieved Document Information: {state["search"]}
"""
    
    prompt=SystemMessage(content=base)
    messages = [prompt] + state["messages"]
    
    with gemini_semaphore:
        result=model.invoke(messages)
    
    return {
        "messages":[result]
    }
    
def shouldContinue(state:AgentState)->str:
    lastMessage=state["messages"][-1]
    if(lastMessage.tool_calls):
        return "continue"
    else:
        return "end"
    
graph=StateGraph(AgentState)
graph.add_node("agent",agent)
graph.add_edge(START,"agent")
graph.add_edge("agent",END)

app=graph.compile()

def start(questions: list[str], index: str, texts: str)->list[str]:
    # Build search results for all questions
    print(len(questions))
    searchResult = ""
    for i, question in enumerate(questions):
        search_response = search.invoke({"query": question, "index": index, "texts": texts})
        searchResult += f"Question {i+1}: {question}\nRelevant Context: {str(search_response)}\n\n"
    
    # Format questions as a numbered list for clarity
    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    
    results = app.invoke({
        "messages": [HumanMessage(content=f"Answer these questions in order:\n{questions_text}")],
        "index": index,
        "texts": texts,
        "search": searchResult
    })

    answer = results['messages'][-1].content.strip()
    answer=answer.replace("json","").replace("```","")
    if(not answer.endswith("]")):
        answer += "]"
    print("Raw answer from model:")
    print(answer)
    try:
        # Try to parse as JSON first
        if answer.startswith('[') and answer.endswith(']'):
            answers = json.loads(answer)
        else:
            # Fallback to ast.literal_eval
            answers = ast.literal_eval(answer)
        print("Parsed answers:", answers)
        if not isinstance(answers, list):
            raise ValueError(f"Expected a list of answers, got {type(answers)}")
        
        # Ensure all answers are strings
        answers = [str(ans) for ans in answers]
        print(len(answers),len(questions))
        
        if len(answers) != len(questions):
            # Pad with error messages if needed
            if len(answers) < len(questions):
                answers.extend([f"Missing answer for question {i+1}" for i in range(len(answers), len(questions))])
            else:
                answers = answers[:len(questions)]
        print("answers",answers)
        return answers
        
    except (json.JSONDecodeError, ValueError, SyntaxError) as e:
        # Return error messages for all questions
        error_answers = [f"Error parsing response: {str(e)}" for _ in questions]
        return error_answers