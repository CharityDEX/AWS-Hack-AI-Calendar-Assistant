from fastapi import FastAPI, Depends
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import Request
from starlette.config import Config
from google.oauth2.credentials import Credentials
import gradio as gr
import os
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from gradio import ChatMessage
from google.oauth2.credentials import Credentials
from email_graph import create_email_graph
import gradio as gr
import os
load_dotenv()

app = FastAPI()
email_graph = create_email_graph()

# OAuth settings
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
SECRET_KEY = 'test' # This is used for encrypting session data
SCOPE = "openid email profile https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send"

# Set up OAuth
config_data = {'GOOGLE_CLIENT_ID': GOOGLE_CLIENT_ID, 'GOOGLE_CLIENT_SECRET': GOOGLE_CLIENT_SECRET}
starlette_config = Config(environ=config_data)
oauth = OAuth(starlette_config)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': SCOPE, 'access_type': 'offline'},
)

# Add session middleware to handle user sessions using the provided secret key
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Dependency to get the current user from the session
def get_user(request: Request):
    user = request.session.get('user')
    if user:
        #print(user)
        return user['name']
    return None

# Public route that determines whether the user is logged in or not
@app.get('/')
def public(request: Request, user = Depends(get_user)):
    # Get the root URL for routing (using Gradio's utility function)
    root_url = gr.route_utils.get_root_url(request, "/", None)
    if user:
        return RedirectResponse(url=f'{root_url}/gradio/')
    else:
        return RedirectResponse(url=f'{root_url}/main/')
    
# Logout route to clear the user's session
@app.route('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url='/')

# Login route that triggers the OAuth2 login process
@app.route('/login')
async def login(request: Request):
    root_url = gr.route_utils.get_root_url(request, "/login", None)
    # Where Google will redirect after login. IMPORTANT!!! should be the same as the one registered in Google Cloud Console Add Authorized redirect URIs
    redirect_uri = f"{root_url}/auth" 
    #print("Redirecting to", redirect_uri)
    return await oauth.google.authorize_redirect(request, redirect_uri, access_type="offline")

# return here after logged in
@app.route('/auth')
async def auth(request: Request):
    try:
        token_data = await oauth.google.authorize_access_token(request)
    except OAuthError:
        #print("Error getting access token", str(OAuthError))
        return RedirectResponse(url='/')
    
    request.session['user'] = dict(token_data)["userinfo"]
    request.session['access_token'] = dict(token_data)["access_token"]
    request.session['refresh_token'] = dict(token_data)["refresh_token"]

    #print("Redirecting to /gradio")
    return RedirectResponse(url='/gradio')

def convert_langchain_to_gradio(messages):
    gradio_messages = []
    for msg in messages:
        if isinstance(msg, AIMessage):
            gradio_messages.append(ChatMessage(role="assistant", content=msg.content))
        elif isinstance(msg, HumanMessage):
            gradio_messages.append(ChatMessage(role="user", content=msg.content))
    return gradio_messages

def load_chat_from_id(gr_state):
    id = str(gr_state["email"])
    config = {"configurable": {"thread_id": id}}
    #state = rag_graph.get_state(config=config)
    return []#convert_langchain_to_gradio(state.values.get("messages", ""))

def init_chatbot(gr_state, request: gr.Request):
    email = request.session.get('user', {}).get('email')
    gr_state["email"] = email
    gr_state["access_token"] = request.session["access_token"]
    gr_state["refresh_token"] = request.session["refresh_token"]

    config = {"configurable": {"thread_id": email}}
    #state = rag_graph.get_state(config=config)
    #print("\n\nMESSAGE:\n " + str(state.values.get("messages", "")) + "\n\n")

    return gr_state, f"## Welcome to CrawlAI, {email}!", []#load_chat_from_id(gr_state)

async def ask_question(question, history: list, gr_state):
    # get thread id
    config = {"configurable": {"thread_id": gr_state["email"]}}

    #history.append({"role": "human", "content": question})
    history.append({"role": "user", "content": question})

    #print("\n\nTHREAD ID: " + str(config))

    '''
    graph_start_time: str
    last_email_check_time: str
    meeting_slot_start: str
    meeting_slot_end: str
    participant_info: dict[str, tuple[bool, str]] # key: email value: (confirmed, last datetime sent)
    meeting_duration_minutes: int
    meeting_description: str
    organizer_name: str
    access_token: str
    refresh_token: str
    background_task_running: bool
    '''

    s = {
        "meeting_title": "Apple Pie Discussion",
        "meeting_slot_start": "2024-11-23 8:00:00",
        "meeting_slot_end": "2024-11-23 9:00:00",
        "participant_info": {
            #"alexander.g.anokhin@gmail.com": (False, "2024-11-17 20:00:00"),
            "aanokhin@scu.edu": (False, "2024-11-17 20:00:00")
            #"mliashch@scu.edu": (False, "2024-11-17 20:00:00")
        },
        "meeting_duration_minutes": 20,
        "organizer_name": "bobby",
        "organizer_email": gr_state["email"],
        "access_token": gr_state["access_token"],
        "refresh_token": gr_state["refresh_token"],
        "meeting_description": "In this meeting we will discuss apple pie."
    }

    response = email_graph.invoke(s, config=config)
    #response = email_graph.invoke({"messages": [HumanMessage(content=question)], "access_token": gr_state["access_token"], "refresh_token": gr_state["refresh_token"]}, config=config)
    history.append({"role": "assistant", "content": "hi"})

    #history.append({"role": "assistant", "content": response["messages"][-1].content})

    return "", history


# input: time slot, meeting info (participants, duration, description)
# output: start the email async task
#def start_emailing_graph():

    

with gr.Blocks() as login_page:
    btn = gr.Button("Login")
    _js_redirect = """
    () => {
        url = '/login' + window.location.search;
        window.open(url, '_blank');
    }
    """
    btn.click(None, js=_js_redirect)

app = gr.mount_gradio_app(app, login_page, path="/main")

# css to be able to dynamically scale gr.Chatbot vertically 
main_chatbot_css = """
#chatbot {
    flex-grow: 1 !important;
    overflow: auto !important;
}
"""

with gr.Blocks(css=main_chatbot_css) as chatbot_page:
    gr_state = gr.State({})
    chat_history_box = None    

    with gr.Row():
        # scale does not work as expected but whatever
        with gr.Column(scale=8):
            welcome_text = gr.Markdown("Welcome to Calendar Bot!")

        with gr.Column(scale=2):
            gr.Button("Logout", link="/logout")

    # chat history component
    #chat_history_box = gr.Chatbot(
    #    show_label=False, 
    #    scale=1, 
    #    elem_id="chatbot", 
    #    bubble_full_width=False, 
    #    type="messages")

    # input component
    #input_box = gr.MultimodalTextbox(
    #    interactive=True,
    #    show_label=False,
    #    scale=0,
    #    file_count="multiple",
    #    placeholder="Enter message or upload file...")
    
    chatbot = gr.Chatbot(type="messages", label="Chatbot")
    msg = gr.Textbox(label="Ask your question")
    msg.submit(ask_question, [msg, chatbot, gr_state], [msg, chatbot])

    # user inputs message
    #user_message_step = input_box.submit(add_user_message, [chat_history_box, input_box], [chat_history_box, input_box])
    # bot processes message (iterator, streaming)
    #bot_message_step = user_message_step.then(bot_stream_graph, [chat_history_box, gr_state], chat_history_box, api_name="bot_response")
    # clear the output field and make it interactive again
    #bot_message_step.then(lambda: gr.MultimodalTextbox(interactive=True), None, [input_box])

    # attach function to run on first load
    chatbot_page.load(init_chatbot, gr_state, [gr_state, welcome_text, chatbot])
    chatbot_page.queue()

app = gr.mount_gradio_app(app, chatbot_page, path="/gradio", auth_dependency=get_user)

