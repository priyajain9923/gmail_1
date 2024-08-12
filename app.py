import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import openai
import nltk
from nltk.corpus import stopwords

# Define the scope for Gmail API access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Cache the download of NLTK stopwords
@st.cache_resource
def download_nltk_stopwords():
    nltk.download('stopwords')
    return set(stopwords.words('english'))

stop_words = download_nltk_stopwords()

# Authentication and API service
@st.cache_resource
def authenticate_user():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8501)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
    return creds

@st.cache_resource
def get_gmail_service():
    creds = authenticate_user()
    service = build('gmail', 'v1', credentials=creds)
    return service

def get_emails(service, label='SPAM', max_results=30):
    try:
        results = service.users().messages().list(userId='me', labelIds=[label], maxResults=max_results).execute()
        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            snippet = msg_data.get('snippet', '')
            emails.append(snippet)

        return emails
    except Exception as e:
        st.error(f"Failed to retrieve emails: {e}")
        return []

def clean_email_text(text):
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = text.lower()
    words = text.split()
    words = [word for word in words if word not in stop_words]
    return ' '.join(words)

def generate_word_cloud(emails):
    combined_text = ' '.join([clean_email_text(email) for email in emails])
    
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        max_words=50, 
        background_color='black',
        colormap='plasma',
        contour_color='steelblue',
        contour_width=2,
        prefer_horizontal=1.0,
    ).generate(combined_text)
    
    return wordcloud

def summarize_email(email_text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that summarizes emails."},
            {"role": "user", "content": f"Please summarize the following email:\n\n{email_text}"}
        ],
        temperature=0.5,
        max_tokens=256
    )
    # Accessing the response
    print(response)
    return response.choices[0].message.content.strip()

def analyze_sentiment(email_text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that analyzes sentiment."},
            {"role": "user", "content": f"Analyze the sentiment of the following email:\n\n{email_text}"}
        ],
        temperature=0,
        max_tokens=256
    )
    # Accessing the response
    return response.choices[0].message.content.strip()


# Streamlit App
st.title("Gmail Analysis Tool")

# Sidebar options
option = st.sidebar.selectbox(
    'Choose an option',
    ('Generate Word Cloud', 'Email Summary & Sentiment Analysis')
)

# Authenticate and get the Gmail service
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if st.button('Authenticate with Gmail'):
    st.session_state.service = get_gmail_service()
    st.session_state.authenticated = True
    st.success("Successfully authenticated with Gmail!")

if st.session_state.authenticated:
    service = st.session_state.service
    if option == 'Generate Word Cloud':
        with st.spinner('Generating word cloud...'):
            spam_emails = get_emails(service, label='SPAM', max_results=30)
            if spam_emails:
                wordcloud = generate_word_cloud(spam_emails)
                st.image(wordcloud.to_array())
            else:
                st.write("No spam emails found.")

    elif option == 'Email Summary & Sentiment Analysis':
        with st.spinner('Retrieving latest emails...'):
            latest_emails = get_emails(service, label='INBOX', max_results=10)
            email_choice = st.selectbox('Select an email to analyze', latest_emails)
            if email_choice:
                with st.spinner('Analyzing selected email...'):
                    summary = summarize_email(email_choice)
                    sentiment = analyze_sentiment(email_choice)
                    st.write(f"**Summary:** {summary}")
                    st.write(f"**Sentiment:** {sentiment}")
