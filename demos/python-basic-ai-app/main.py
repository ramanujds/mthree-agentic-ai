import requests

def get_response_from_llm(prompt):
    url = "http://localhost:12434/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_API_KEY"  # Replace with your actual API key
    }
    data = {
        "model": "gemma4:E4B",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Reply in simple words. Do not use any code blocks or markdown formatting. Do not include any steps or instructions. Do not include any disclaimers."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Error: {response.status_code}, {response.text}"

if __name__ == "__main__":
        user_input = "Explain what is kubernetes in simple words."
        response = get_response_from_llm(user_input)
        print(f"Assistant: {response}")