import os
import os.path
import json
import pprint
import requests
import datetime
from dateutil.relativedelta import relativedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL:@SECLEVEL=1'

GROUP_CODE = os.getenv('GROUP_CODE')
SCOPES = ['https://www.googleapis.com/auth/calendar']


def getSchedule():
    Data = {
        "id_grp": GROUP_CODE,  # 1002732
        "date_beg": (datetime.date.today()).strftime("%d.%m.%Y"),
        "date_end": (
            datetime.date.today() + relativedelta(months=1)
        ).strftime("%d.%m.%Y")
    }

    response = requests.post(
        'https://schedule.sumdu.edu.ua/index/json',
        data=Data,
        verify=False,
        timeout=10
    )

    return json.loads(response.text)


def updateEvents(creds):
    scheduleJSON = getSchedule()
    
    try:
        service = build('calendar', 'v3', credentials=creds)

        for ssuEvent in scheduleJSON:
            
            events_result = service.events().list(calendarId='primary', timeMin=now,
                                                maxResults=10, singleEvents=True,
                                                orderBy='startTime').execute()
            events = events_result.get('items', [])

            if not events:
                print('No upcoming events found.')
                return

            # Prints the start and name of the next 10 events
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(start, event['summary'])

    except HttpError as error:
        print('An error occurred: %s' % error)

def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    getSchedule()

if __name__ == '__main__':
    main()