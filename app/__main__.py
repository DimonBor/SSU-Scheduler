import re
import os.path
import json
import logging
import secrets
import requests
import datetime

from waitress import serve
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, render_template, redirect
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import SubmitField, SelectField, IntegerField, validators
from oauthlib import oauth2
if __name__ == "__main__":
    from app import schedule_utils
    from app.db_utils import update_user, delete_user


logging.basicConfig(level="INFO")

requests.packages.urllib3.disable_warnings()
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL:@SECLEVEL=1'

try:
    GROUPS = list(tuple(requests.get("https://schedule.sumdu.edu.ua/index/json?method=getGroups", verify=False).json().items())[1:])
    # fetch group list at startup
except:
    logging.error(f"[{datetime.datetime.now()}] Failed to get groups list!")
    exit(1)

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
UPDATE_TIMEOUT = int(os.getenv('UPDATE_TIMEOUT')) if os.getenv('UPDATE_TIMEOUT') else 30
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/userinfo.email']

DATA = {
    'response_type': 'code',
    'login_redirect_uri': f"{os.getenv('WEB_URL')}/settings",
    'logout_redirect_uri': f"{os.getenv('WEB_URL')}/logout",
    'scope': SCOPES,
    'client_id': CLIENT_ID,
    'prompt': 'consent',
    'access_type': 'offline'
}

URL_DICT = {
    'google_oauth': 'https://accounts.google.com/o/oauth2/v2/auth',
    'token_gen': 'https://oauth2.googleapis.com/token',
    'get_user_info': 'https://www.googleapis.com/oauth2/v3/userinfo'
}

CLIENT = oauth2.WebApplicationClient(CLIENT_ID)

LOGIN_URI = CLIENT.prepare_request_uri(
    uri=URL_DICT['google_oauth'],
    redirect_uri=DATA['login_redirect_uri'],
    scope=DATA['scope'],
    prompt=DATA['prompt'],
    access_type=DATA['access_type']
)
LOGOUT_URI = CLIENT.prepare_request_uri(
    uri=URL_DICT['google_oauth'],
    redirect_uri=DATA['logout_redirect_uri'],
    scope=DATA['scope'],
    prompt=DATA['prompt'],
    access_type=DATA['access_type']
)


app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)
bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)
scheduler = BackgroundScheduler()


class SettingsForm(FlaskForm):
    group = SelectField(
        'Your group',
        [validators.InputRequired()],
        choices=GROUPS)
    schedule_period = SelectField(
        'Period to fetch schedule, days',
        [validators.InputRequired()],
        choices=["7", "14"])
    reminder_minutes = IntegerField(
        'Set reminder before the event, min',
        [validators.InputRequired(), validators.NumberRange(
            max=60,
            min=1,
            message="Reminder should be less than 61 and greater than 0."
        )])
    submit = SubmitField('Submit')


@app.route('/')
def login():
    return redirect(LOGIN_URI)  # get code from Google to perform any action


@app.route('/logout')
def logout():

    code = request.args.get('code')

    if not code:
        return redirect(LOGOUT_URI)  # get code from Google to perform any action

    token_url, headers, body = CLIENT.prepare_token_request(
        URL_DICT['token_gen'],
        authorisation_response=request.url,
        redirect_url=request.base_url,
        code=code
    )

    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(CLIENT_ID, CLIENT_SECRET)
    )

    try:
        CLIENT.parse_request_body_response(json.dumps(token_response.json()))
        uri, headers, body = CLIENT.add_token(URL_DICT['get_user_info'])
        response_user_info = requests.get(uri, headers=headers, data=body)
        email = response_user_info.json()['email']
    except:
        return render_template(
            'error.html',
            error="Google authorization error."
        )

    try:
        delete_user(email)
    except:
        return render_template(
            'error.html',
            error="Can't remove this user."
        )

    logging.info(f"[{datetime.datetime.now()}] Deleted user: {email}")

    return render_template(
        'success.html',
        message=f"User has been deleted successfully. Schedule will no longer update in your calendar."
    )


@app.route('/settings', methods=['GET', 'POST'])
def settings():

    code = request.args.get('code')

    if not code:
        return redirect(LOGIN_URI)

    form = SettingsForm()

    if form.validate_on_submit():

        code = request.args.get('code')

        token_url, headers, body = CLIENT.prepare_token_request(
            URL_DICT['token_gen'],
            authorisation_response=request.url,
            redirect_url=request.base_url,
            code=code
        )

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(CLIENT_ID, CLIENT_SECRET)
        )

        try:
            CLIENT.parse_request_body_response(json.dumps(token_response.json()))
            uri, headers, body = CLIENT.add_token(URL_DICT['get_user_info'])
            response_user_info = requests.get(uri, headers=headers, data=body)
            email = response_user_info.json()['email']

        except:  # not OK response from Google API
            logging.exception(f"[{datetime.datetime.now()}]: Exception occurred!!!")
            return render_template(
                'error.html',
                error="Google authorization error."
            )

        try:
            update_user(  # Create or update user in DB
                email,
                token_response.json(),
                popup_reminder=int(form.reminder_minutes.data),
                group_code=int(form.group.data),
                fetch_days=int(form.schedule_period.data)
            )
        except:
            return render_template(
                'error.html',
                error="Failed to create user."
            )

        logging.info(f"[{datetime.datetime.now()}]: Created user: {email}")

        return render_template(
            'success.html',
            message=f"User has been configured successfully. Schedule will appear in your calendar in {UPDATE_TIMEOUT} minutes."
        )

    return render_template('settings.html', form=form)


if __name__ == '__main__':

    logging.info(
        f"[{datetime.datetime.now()}]: Starting scheduler.\n" +
        "\tParams:\n" +
        f"\t\tUPDATE_TIMEOUT: {UPDATE_TIMEOUT}\n"
    )

    scheduler.add_job(schedule_utils.update_events, 'interval', minutes=UPDATE_TIMEOUT, max_instances=1)
    scheduler.start()

    serve(app, host='0.0.0.0', port=5000, url_scheme=re.match(r'[^:]*',os.getenv('WEB_URL'))[0])
