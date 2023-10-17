import datetime
import json
import logging
import dateutil.tz as dtz
import requests
from hashlib import sha256

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.db_utils import get_users, get_access_token


def get_schedule(group_code, schedule_period):
    data = {
        "method": "getSchedules",
        "id_grp": group_code,
        "date_beg": (datetime.date.today()).strftime("%d.%m.%Y"),
        "date_end": (
                datetime.date.today() + datetime.timedelta(days=schedule_period)
        ).strftime("%d.%m.%Y")
    }  # Creating payload for selected period

    try:
        response = requests.post(
            'https://schedule.sumdu.edu.ua/index/json',
            params=data,
            verify=False,
            timeout=10
        )
    except:
        logging.error(f"[{datetime.datetime.now()}]: Error of SSU Schedule")
        return None

    return json.loads(response.text)


def update_events():
    logging.info(f"[{datetime.datetime.now()}]: Starting updates.")

    time_start = datetime.datetime.now()

    for user in get_users():
        try:

            schedule_events = get_schedule(user.group_code, user.fetch_days)
            schedule_hashes = [  # compute all hashes for SSU events
                sha256(json.dumps(event, sort_keys=True).encode('utf-8')).hexdigest()[:10]
                for event in schedule_events
            ]

            access_token = get_access_token(user)
            if not access_token: continue

            service = build('calendar', 'v3', credentials=Credentials(token=access_token))

            calendars_list = service.calendarList().list().execute()
            calendars = calendars_list.get('items', [])

            if 'SSU Schedule' not in [entry['summary'] for entry in calendars]:
                calendar_id = service.calendars().insert(body={'summary': 'SSU Schedule'}).execute()['id']
                # Creating the calendar

                service.calendarList().update(  # Enable the calendar in list and update color to match SSU style
                    calendarId=calendar_id,
                    body={
                        'colorId': '16',
                        'selected': True
                    }).execute()

            for entry in calendars:
                if entry['summary'] == 'SSU Schedule':
                    calendar_id = entry['id']

            g_events = service.events().list(calendarId=calendar_id).execute()['items']

            for g_event in g_events:  # removing obsolete events
                logging.debug(f"[{datetime.datetime.now()}]: Got event from Google: {g_event}")
                try:
                    if not g_event['extendedProperties']['private']['ssuHash'] in schedule_hashes:
                        service.events().delete(calendarId=calendar_id, eventId=g_event['id']).execute()
                        del g_events[g_events.index(g_event)]
                except KeyError:  # no description - no event
                    service.events().delete(calendarId=calendar_id, eventId=g_event['id']).execute()
                    del g_events[g_events.index(g_event)]

            for ssuEvent in schedule_events:
                if not ssuEvent['NAME_DISC']:
                    continue  # Skipping empty pairs

                if (sha256(json.dumps(ssuEvent, sort_keys=True).encode('utf-8')).hexdigest()[:10] in  # Skipping created
                        [g_event['extendedProperties']['private']['ssuHash'] for g_event in g_events]):  # events
                    continue

                timeStart = datetime.datetime.strptime(  # Converting Schedule timeframe to isoformat
                    f"{ssuEvent['DATE_REG']} {ssuEvent['TIME_PAIR'][:5]}",
                    "%d.%m.%Y %H:%M"
                ).replace(tzinfo=dtz.gettz("Europe/Kiev")).isoformat()

                timeEnd = datetime.datetime.strptime(  # Converting Schedule timeframe to isoformat
                    f"{ssuEvent['DATE_REG']} {ssuEvent['TIME_PAIR'][6:]}",
                    "%d.%m.%Y %H:%M"
                ).replace(tzinfo=dtz.gettz("Europe/Kiev")).isoformat()

                event = {  # Creating event payload
                    'summary': ssuEvent['NAME_DISC'],
                    'location': ssuEvent['NAME_AUD'] if ssuEvent['NAME_AUD'] else 'Online',
                    'description': f"{ssuEvent['NAME_FIO']}\n{ssuEvent['NAME_STUD']}\n\n{ssuEvent['COMMENT']}",
                    'start': {
                        'dateTime': timeStart,
                        'timeZone': 'Europe/Kyiv',
                    },
                    'end': {
                        'dateTime': timeEnd,
                        'timeZone': 'Europe/Kyiv',
                    },
                    'recurrence': None,
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'popup', 'minutes': user.popup_reminder},
                        ],
                    },
                    "extendedProperties": {
                        "private": {
                            "ssuHash": f"{sha256(json.dumps(ssuEvent, sort_keys=True).encode('utf-8')).hexdigest()[:10]}"
                        }
                    }
                }

                event = service.events().insert(  # Inserting Events
                    calendarId=calendar_id,
                    body=event
                ).execute()

                logging.debug(f"[{datetime.datetime.now()}]: Event created: {event.get('htmlLink')}")

            service.close()  # closing session, Important!

        except:
            logging.exception(f"[{datetime.datetime.now()}]: Exception occurred!!!")

    logging.info(
        f"[{datetime.datetime.now()}]: Finished updates in {(datetime.datetime.now() - time_start).total_seconds()} seconds."
    )
