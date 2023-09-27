from aiohttp import web, ClientSession, BasicAuth
import datetime


AIRFLOW_API = "http://localhost:8080/api/v1"
AIRFLOW_USER = 'jane'
AIRFLOW_PASSWORD = 'jane'


app = web.Application()


async def on_startup(app):
    app['airflow_session'] = ClientSession()


async def on_shutdown(app):
    try:
        session = app['airflow_session']
        await session.close()
    except KeyError:
        pass


app.on_shutdown.append(on_shutdown)
app.on_startup.append(on_startup)


async def hello(request):
    return web.Response(text="Hello, world")


async def run(request):
    cmd = request.match_info['cmd']
    data = await request.json()
    print(data)
    try:
        file_path = data['filepath']
        email = data['email']
        appversion = data.get("appversion", "1.0.0")
        print(f"File path {file_path}, email {email}, cmd {cmd}")
    except (KeyError, TypeError, ValueError) as e:
        raise web.HTTPBadRequest(
            text='Missing required values') from e

    dag_data = {
        "logical_date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), # + "Z",
        "conf": {
            "filepath": file_path,
            "email": email,
            "appversion": appversion
        },
    }
    print(f"DAG data {dag_data}")

    # post event to kafka topic instead
    async with app['airflow_session'].post(
        f'{AIRFLOW_API}/dags/{cmd}/dagRuns',
        json=dag_data,
        headers={'Content-Type': 'application/json'},
        auth=BasicAuth(AIRFLOW_USER, AIRFLOW_PASSWORD),
    ) as resp:
        status = resp.status
        response_json = await resp.json()

    return web.Response(text=f"Accepted, dag status {status}, response {response_json} ")


app.add_routes([web.post('/run/{cmd}', run)])
app.add_routes([web.post('/run/{cmd}/', run)])
app.add_routes([web.get('/', hello)])
web.run_app(app, port=8085)
