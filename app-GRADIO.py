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
from langchain_openai import ChatOpenAI
from email_graph import pst_to_utc, utc_to_pst
from datetime import datetime, timedelta
from googleapiclient.discovery import build

load_dotenv()

app = FastAPI()
email_graph = create_email_graph()
time_selector_llm = ChatOpenAI(temperature=0)
format_string = "%Y-%m-%d %H:%M:%S"

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

async def process_data(gr_state, title_input, interval_start_input, interval_end_input, duration_input, meeting_description, participant_input):
    print(" PARTICIPANT INPUT: " + str(participant_input))

    participant_emails = participant_input.split()
    email_dict = {email: (False, "2024-01-01 09:00:00") for email in participant_emails}

    s = {
        "participant_emails": participant_emails,
        "meeting_interval_start_date": interval_start_input,
        "meeting_interval_end_date": interval_end_input,
        "participant_info": email_dict,
        "meeting_duration": duration_input,
        "meeting_description": meeting_description,
        "access_token": gr_state["access_token"],
        "refresh_token": gr_state["refresh_token"],
        "organizer_email": gr_state["email"],
        "organizer_name": gr_state["user_name"],
        "meeting_title": title_input
    }

    slots = get_availability_slots(s)

    # update gradio elements
    yield ["", "", "", "", "", "", gr.Button("Submit", interactive=False), "Emails have been sent. If all participants accept, google calendar event will be created. Please monitor your inbox for live info."]

    if slots:
        best_slot = select_best_slot(duration_input, slots)
        s["meeting_slot_start"] = best_slot

        time_obj = datetime.strptime(best_slot, format_string)
        updated_time_obj = time_obj + timedelta(minutes=duration_input)
        updated_time_string = updated_time_obj.strftime(format_string)
        s["meeting_slot_end"] = updated_time_string

        config = {"configurable": {"thread_id": gr_state["email"]}}
        email_graph.invoke(s, config=config)

def dates_to_strings(dates):
    string_tuples = []
    for slot_start, slot_end in dates:
        string_tuples.append((slot_start.strftime(format_string), slot_end.strftime(format_string)))
        
    return string_tuples

def get_availability_slots(s):
    
    meeting_interval_start_date = s["meeting_interval_start_date"]
    meeting_interval_end_date = s["meeting_interval_end_date"]
    participant_emails = s["participant_emails"]
    meeting_duration_minutes = s["meeting_duration"]

    client_id = os.environ["GOOGLE_CLIENT_ID"]
    client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
    creds = Credentials(token=s["access_token"], refresh_token=s["refresh_token"], client_id=client_id, client_secret=client_secret)
    calendar_service = build('calendar', 'v3', credentials=creds)

    start_date = datetime.strptime(meeting_interval_start_date, format_string)
    end_date = datetime.strptime(meeting_interval_end_date, format_string)

    start_date = pst_to_utc(start_date)
    end_date = pst_to_utc(end_date)

    body = {
        "timeMin": start_date.isoformat() + "Z",
        "timeMax": end_date.isoformat() + "Z",
        "items": [{"id": email} for email in participant_emails]
    }
    freebusy_result = calendar_service.freebusy().query(body=body).execute()

    all_busy_periods = []
    for calendar in freebusy_result['calendars'].values():
        for busy_period in calendar.get('busy', []):
            busy_start = datetime.fromisoformat(busy_period['start'][:-1])
            busy_end = datetime.fromisoformat(busy_period['end'][:-1])
            all_busy_periods.append((busy_start, busy_end))

    all_busy_periods.sort()
    merged_busy_periods = []
    for busy_start, busy_end in all_busy_periods:
        if not merged_busy_periods or merged_busy_periods[-1][1] < busy_start:
            merged_busy_periods.append((busy_start, busy_end))
        else:
            merged_busy_periods[-1] = (merged_busy_periods[-1][0], max(merged_busy_periods[-1][1], busy_end))

    available_slots = []
    current_start = start_date
    for busy_start, busy_end in merged_busy_periods:
        if busy_start - current_start >= timedelta(minutes=meeting_duration_minutes):
            available_slots.append((utc_to_pst(current_start), utc_to_pst(busy_start)))
        current_start = busy_end

    if end_date - current_start >= timedelta(minutes=meeting_duration_minutes):
        available_slots.append((utc_to_pst(current_start), utc_to_pst(end_date)))

    return dates_to_strings(available_slots)

def select_best_slot(duration, slots):
    selector_prompt = f'''
        You are a specialized agent made to select meeting time slots. You will be provided
        by a list of times showing intervals when meeting participants are all available, each of which is a tuple of datetime strings (one for start of interval, one for end).
        Out of these, please select 1 time slot {duration} minutes long that would be most convenient for a work meeting. Prefer a time
        slot that is not too late at night or too early in the morning, and avoid weekends if you can (for context it is 2024 right now).
        Also if possible, prefer to output the slot starting at a round time (example on the hour or on the half-hour).
        Please output a just a string as your answer, it being the selected time slot start
        datetime (in the format {format_string}). Please remember that your selected time slot must fit
        into the provided ones, must be of duration {duration} minutes, and must be properly output in the format {format_string}.
        Provided time slots (in tuples, start and end): {slots}
        Your selected most convenient time slot:
    '''
    response = time_selector_llm.invoke(selector_prompt)
    return response.content

def init_chatbot(gr_state, request: gr.Request):
    email = request.session.get('user', {}).get('email')
    gr_state["user_name"] = request.session.get('user', {}).get('name')
    gr_state["email"] = email
    gr_state["access_token"] = request.session["access_token"]
    gr_state["refresh_token"] = request.session["refresh_token"]

    return gr_state, f"## Welcome to Calendar Agent, {email}!"

def check_inputs(input1, input2, input3, input4, input5, input6):
    print("\nCHANGING!\n")
    print("\nCHANGE: \n" + input1)
    if input1 and input2 and input3 and input4 and input5 and input6:  # Add conditions for all required inputs
        return gr.Button("Submit", interactive=True)  # Enable button
    else:
        return gr.Button("Submit", interactive=False)  # Disable button

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

with gr.Blocks() as chatbot_page:
    gr_state = gr.State({})
    chat_history_box = None    

    with gr.Row():
        # scale does not work as expected but whatever
        with gr.Column(scale=8):
            welcome_text = gr.Markdown("Welcome to Calendar Bot!")

        with gr.Column(scale=2):
            gr.Button("Logout", link="/logout")
    
    title_input = gr.Textbox(label="Meeting Title:")
    interval_start_input = gr.DateTime(label="Interval Start Date/Time:", type="string")
    interval_end_input = gr.DateTime(label="Interval End Date/Time:", type="string")
    duration_input=gr.Number(label="Meeting duration (minutes):")
    meeting_description=gr.Textbox(label="Meeting description:")
    participant_input=gr.Textbox(label="Participant emails (separated by spaces):")

    submit_button = gr.Button("Submit", interactive=False)

    output_text = gr.Textbox(label="Output:", interactive=False)

    interval_start_input.change(check_inputs, [title_input, interval_start_input, interval_end_input, duration_input, meeting_description, participant_input], submit_button)
    interval_end_input.change(check_inputs, [title_input, interval_start_input, interval_end_input, duration_input, meeting_description, participant_input], submit_button)
    duration_input.change(check_inputs, [title_input, interval_start_input, interval_end_input, duration_input, meeting_description, participant_input], submit_button)
    meeting_description.change(check_inputs, [title_input, interval_start_input, interval_end_input, duration_input, meeting_description, participant_input], submit_button)
    participant_input.change(check_inputs, [title_input, interval_start_input, interval_end_input, duration_input, meeting_description, participant_input], submit_button)
    title_input.change(check_inputs, [title_input, interval_start_input, interval_end_input, duration_input, meeting_description, participant_input], submit_button)

    submit_button.click(process_data, [gr_state, title_input, interval_start_input, interval_end_input, duration_input, meeting_description, participant_input], [title_input, interval_start_input, interval_end_input, duration_input, meeting_description, participant_input, submit_button, output_text])

    # attach function to run on first load
    chatbot_page.load(init_chatbot, gr_state, [gr_state, welcome_text])
    #chatbot_page.queue()

app = gr.mount_gradio_app(app, chatbot_page, path="/gradio", auth_dependency=get_user)

