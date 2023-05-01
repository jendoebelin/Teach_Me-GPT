from flask import Flask, render_template, request, session
import openai
import re
import requests
import json
from PIL import Image
import io
import base64

openai.api_key = open("key.txt", "r").read().strip("\n")
preprompt = open("preprompt.txt", "r").read().strip("\n")

url = "http://127.0.0.1:7860/sdapi/v1/txt2img"

app = Flask(__name__)
app.secret_key = "mysecretkey"

def get_img(prompt):
    img_url = None
    try:
        payload = json.dumps({
        "prompt": prompt,
        "steps": 25, 
        "cfg_scale":10
        })
        headers = {
        'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        r = response.json()
        #print(r)
        image_64 = r["images"][0]
        #for i in r['images']:
        #image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
        #img_url = Image.open(io.BytesIO(base64.b64decode(image_64)))
        img_url = image_64
        
    except Exception as e:
        # if it fails (e.g. if the API detects an unsafe image), use a default image
        img_url = "https://pythonprogramming.net/static/images/imgfailure.png"
        print(e)
        
    return img_url

def enforce_four_answers(answers):
    answer_texts = [answer.split(':', 1)[-1].strip() for answer in answers]

    if len(answer_texts) < 4:
        for i in range(len(answer_texts), 4):
            answer_texts.append(f"[No action]")
    elif len(answer_texts) > 4:
        answer_texts = answer_texts[:4]

    return answer_texts


# Define a function to generate a chat response using the OpenAI API
def chat(inp, message_history, role="user"):

    # Append the input message to the message history
    message_history.append({"role": role, "content": f"{inp}"})

    # Generate a chat response using the OpenAI API
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message_history
    )

    # Grab just the text from the API completion response
    reply_content = completion.choices[0].message.content

    # Append the generated response to the message history
    message_history.append({"role": "assistant", "content": f"{reply_content}"})

    # Return the generated response and the updated message history
    return reply_content, message_history


@app.route('/', methods=['GET', 'POST'])
def home():
    title = "Teach_Me-GPT"
    button_messages = {}
    button_states = {}
    paragraph = ""
    question = []
    answer_texts = []
    
    if 'total_questions' not in session:
        session['total_questions'] = 0

    if 'correct_answers' not in session:
        session['correct_answers'] = 0

    if request.method == 'GET':
        session['message_history'] = [{"role": "user", "content": preprompt},
                                   {"role": "assistant", "content": f"""OK, I understand. Begin when you're ready."""}]

    message_history = session['message_history']
    reply_content, message_history = chat("Begin", message_history)

    try:
        paragraph, question_text = reply_content.split("?", 1)
        question_text, _ = question_text.split("answer 1:", 1)
        paragraph = paragraph.strip()
        question_text = question_text.strip()
    except ValueError:
        print("Error: '?' or 'answer 1:' not found in reply_content")


    
    pattern = r"question:(.*?)\n\nanswer"
    match = re.search(pattern, reply_content)
    
    answers = re.findall(r"answer \d:.*", reply_content)
    answers = enforce_four_answers(answers)
    question = re.findall(r"question:.*", reply_content)
    print("regex:")
    print(answers)
    
    if match:
        question = match.group(0)
        print(question)
    else:
        print("Question not found")
    
    
    answer_texts = [answer.split(':', 1)[-1].strip() for answer in answers]

    for i, answer_text in enumerate(answer_texts):
        button_messages[f"button{i+1}"] = answer_text


    for button_name in button_messages.keys():
        button_states[button_name] = False
        
        # Get the question without the answers
    try:
        question = reply_content.split("? ", 1)[0].strip() + "?"
    except IndexError:
        print("Error: 'question' not found in reply_content")
    
       
        
        # Store button_messages in the session for later use
    session['button_messages'] = button_messages

    if request.method == 'POST':
        message_history = session['message_history']
        
        # Retrieve button_messages from the session
        button_messages = session.get('button_messages', {})
        
        button_name = request.form.get('button_name')
        if button_name == "start_over":
            return home()

        button_states[button_name] = True
        message = button_messages.get(button_name)

        reply_content, message_history = chat(message, message_history)

        text = reply_content.split("answer 1")[0]
        answers = re.findall(r"answer \d:.*", reply_content)
        answers = enforce_four_answers(answers)

        answer_texts = [answer.split(':', 1)[-1].strip() for answer in answers]

        for i, answer_text in enumerate(answer_texts):
            button_messages[f"button{i+1}"] = answer_text
        for button_name in button_messages.keys():
            button_states[button_name] = False

        if button_name == "button1":  # Assuming the first answer is always the correct answer
            session['correct_answers'] += 1
        session['total_questions'] += 1


    session['message_history'] = message_history
    session['button_messages'] = button_messages

    try:
        paragraph, question_text = reply_content.split("?", 1)
        question_text, _ = question_text.split("answer 1:", 1)
        paragraph = paragraph.strip()
        question_text = question_text.strip()
    except ValueError:
        print("Error: '?' or 'answer 1:' not found in reply_content")


    # Get the question without the answers
        
    print(f" {reply_content}")
    
    
    # Store the question without the answers in the session
    session['question'] = question
    
    img_url = get_img(paragraph)

    total_questions = session['total_questions']
    correct_answers = session['correct_answers']

    return render_template('home.html', title=title, image_url=img_url, paragraph=paragraph, question=question_text, answer_texts=answer_texts, button_messages=button_messages, button_states=button_states, total_questions=total_questions, correct_answers=correct_answers)

if __name__ == '__main__':
    app.run(debug=True, port=5001)

