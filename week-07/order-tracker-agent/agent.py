from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

orders={
    "1234":"Shipped, arrives Monday",
    "2345":"Packed, ships tomorrow"
}

@tool
def get_order_status(order_id:str) -> str:
    """Check for delivery status of an order. Use when you are asked to find the status of the order with order id as input"""
    return orders.get(order_id, f"No order found with id {order_id}")

@tool
def cancel_order(order_id:str) -> str:
    """Check if the order exists if exists cancel the order. Use when you are asked to cancel an order with order id as input"""
    if(orders.get(order_id)):
        orders[order_id]="Cancelled by you.."
        return f"Order {order_id} cancelled by you."
    else:
        return f"No order found with id {order_id}"

def approved_by_human(name, args):
    answer = input(f"Approval needed: {name}({args}). Allow? (y/n): ").lower()
    return answer in("y", "yes")

tools = [get_order_status, cancel_order]
tools_by_name = {t.name :t for t in tools}
needs_approval = {cancel_order.name}

model = ChatOpenAI(model="docker.io/ai/gemma4:E4B", base_url="http://localhost:12434/v1", api_key="xyz")

model_with_tools=model.bind_tools(tools)
messages=[]

print("Chat to Order Tracker Assistant:")
while True:
    user_input = input("You : ")
    if user_input in ("quit", "exit"):
        break
    messages.append(HumanMessage(user_input))
    reply = model_with_tools.invoke(messages)

    while reply.tool_calls:
        messages.append(reply)
        for call in reply.tool_calls:
            print(f"Model ask for {call['name']}({call['args']})")
            selected_tool=tools_by_name.get(call["name"])
            if selected_tool is None:
                result = f"Unknow tool {call['name']}"
            elif call["name"] in needs_approval and not approved_by_human(call["name"],call["args"]):
                result = "The user has denied this action, no further action to be taken"
            else:
                result = selected_tool.invoke(call['args'])
            print(f" [Tool returned : {result}]")
            messages.append(ToolMessage(str(result),tool_call_id=call["id"]))
        reply = model_with_tools.invoke(messages)
    messages.append(reply)
    print("AI : ", reply.content)

print(orders)
