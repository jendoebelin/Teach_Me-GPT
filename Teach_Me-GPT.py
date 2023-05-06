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

def enforce_four_Answers(Answers):
    Answer_texts = [Answer.split(':', 1)[-1].strip() for Answer in Answers]

    if len(Answer_texts) < 4:
        for i in range(len(Answer_texts), 4):
            Answer_texts.append(f"[No action]")
    elif len(Answer_texts) > 4:
        Answer_texts = Answer_texts[:4]

    return Answer_texts


# Define a function to generate a chat response using the OpenAI API
def chat(inp, message_history, role="user"):

    # Append the input message to the message history
    message_history.append({"role": role, "content": f"{inp}"})

    # Generate a chat response using the OpenAI API
    completion = openai.ChatCompletion.create(
        model="gpt-4",
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
    Question = []
    Answer_texts = []
    
    if 'total_Questions' not in session:
        session['total_Questions'] = 0

    if 'correct_Answers' not in session:
        session['correct_Answers'] = 0

    if request.method == 'GET':
        session['message_history'] = [{"role": "user", "content": preprompt},
                                   {"role": "assistant", "content": f"""OK, I understand. Begin when you're ready."""}]

    message_history = session['message_history']
    reply_content, message_history = chat("Begin", message_history)

    try:
        paragraph, Question_text = reply_content.split("?", 1)
        Question_text, _ = Question_text.split("Answer 1:", 1)
        paragraph = paragraph.strip()
        Question_text = Question_text.strip()
    except ValueError:
        print("Error: '?' or 'Answer 1:' not found in reply_content")


    
    pattern = r"Question:(.*?)\n\nAnswer"
    match = re.search(pattern, reply_content)
    
    Answers = re.findall(r"Answer \d:.*", reply_content)
    Answers = enforce_four_Answers(Answers)
    Question = re.findall(r"Question:.*", reply_content)
    print("regex:")
    print(Answers)
    
    if match:
        Question = match.group(0)
        print(Question)
    else:
        print("Question not found")
    
    
    Answer_texts = [Answer.split(':', 1)[-1].strip() for Answer in Answers]

    for i, Answer_text in enumerate(Answer_texts):
        button_messages[f"button{i+1}"] = Answer_text


    for button_name in button_messages.keys():
        button_states[button_name] = False
        
        # Get the Question without the Answers
    try:
        Question = reply_content.split("? ", 1)[0].strip() + "?"
    except IndexError:
        print("Error: 'Question' not found in reply_content")
    
       
        
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

        text = reply_content.split("Answer 1")[0]
        Answers = re.findall(r"Answer \d:.*", reply_content)
        Answers = enforce_four_Answers(Answers)

        Answer_texts = [Answer.split(':', 1)[-1].strip() for Answer in Answers]

        for i, Answer_text in enumerate(Answer_texts):
            button_messages[f"button{i+1}"] = Answer_text
        for button_name in button_messages.keys():
            button_states[button_name] = False

        if button_name == "button1":  # Assuming the first Answer is always the correct Answer
            session['correct_Answers'] += 1
        session['total_Questions'] += 1


    session['message_history'] = message_history
    session['button_messages'] = button_messages

    try:
        paragraph, Question_text = reply_content.split("?", 1)
        Question_text, _ = Question_text.split("Answer 1:", 1)
        paragraph = paragraph.strip()
        Question_text = Question_text.strip()
    except ValueError:
        print("Error: '?' or 'Answer 1:' not found in reply_content")


    # Get the Question without the Answers
        
    print(f" {reply_content}")
    
    
    # Store the Question without the Answers in the session
    session['Question'] = Question
    
    img_url = get_img(paragraph)

    total_Questions = session['total_Questions']
    correct_Answers = session['correct_Answers']

    return render_template('home.html', title=title, image_url=img_url, paragraph=paragraph, Question=Question_text, Answer_texts=Answer_texts, button_messages=button_messages, button_states=button_states, total_Questions=total_Questions, correct_Answers=correct_Answers)

if __name__ == '__main__':
    app.run(debug=True, port=5001)

