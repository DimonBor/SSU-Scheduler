# SSU-Scheduler
Middleware app for pushing schedule from [SSU](https://int.sumdu.edu.ua/en//) to Google Calendar.

## Available params
There are a few params that can be customised.

| Env var          | Default value, units | Notes                                                                                          |
|------------------|----------------------|------------------------------------------------------------------------------------------------|
| `UPDATE_TIMEOUT` | 30, mins             | Events update frequency                                                                        |
| `CLIENT_SECRET`  | None                 | Client Secret from https://console.cloud.google.com/apis/credentials                           |
| `CLIENT_ID`      | None                 | Client ID from https://console.cloud.google.com/apis/credentials                               |
| `WEB_URL`        | None                 | Redirect URL base. External app address which will be used by Google to redirect authorization |
| `DEBUG_LEVEL`    | 'INFO'               | Set debug level                                                                                | 

## Basic usage

Deploy the application:
```bash
export CLIENT_SECRET='' && export CLIENT_ID='' && export WEB_URL='http://127.0.0.1:5000' && export UPDATE_TIMEOUT=1 && export DEBUG_LEVEL='DEBUG'
docker compose up -d
```

Or create the `.env` file and put your vars in it.

Also, you can run the dev variant (the only difference is exposed Postres ports):
```bash
docker compose up -d -f docker-compose-dev.yaml
```

Go to web page, complete configuration, and wait till update task will be executed (no longer than `UPDATE_TIMEOUT`)

## Web FAQ

*Q: How to disable scheduler?*

**A: Go to /logout page. This will remove user from app DB and schedule will no longer be updated**

\
*Q: How can I see my current configuration?*

**A: There is no such possibility. All actions are performed with re-authorization with Google. I don't want to write my own authorization system**
**So that just re-login and set desired settings.**

\
*Q: Schedule stopped updating. What happened?*

**A: Try to re-login. Probably refresh token has expired, so you needed to re-login manually(remember about update timeout).**
**If this doesn't help please contact the app owner.**