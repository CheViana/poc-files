from aiohttp import web, ClientSession, BasicAuth
import datetime
import json
from time import sleep
from google.cloud import storage, storage_transfer_v1


app = web.Application()
REF_DICT = 'dict.txt'
WORDS_LIST_BUCKET = "river-sand"
RESULTS_BUCKET = "river-sand"
GCP_CREDS_PATH = "charged-scholar-399420-ab7ede7e134a.json"


def get_random_str():
    return ''.join(
        secrets.choice(string.ascii_lowercase + string.digits) for i in range(8)
    )


def read_blob(bucket_name, blob_name):
    client = storage.Client.from_service_account_json(GCP_CREDS_PATH)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    with blob.open("r") as f:
        return json.load(f)


def write_blob(bucket_name, blob_name, contents):
    client = storage.Client.from_service_account_json(GCP_CREDS_PATH)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(contents))


def wait_on_transfer_job(transfer_operation_name):
    transfer_client = storage_transfer_v1.StorageTransferServiceClient.from_service_account_json(GCP_CREDS_PATH)
    operation = transfer_client.transport.operations_client.get_operation(
        transfer_operation_name
    )
    while not operation.done:
        sleep(1)
        print(f'Operation {transfer_operation_name} is not yet done')
        operation = transfer_client.transport.operations_client.get_operation(
            transfer_operation_name
        )

async def trigger_results_transfer_job():
    client = storage_transfer_v1.StorageTransferServiceAsyncClient.from_service_account_json(GCP_CREDS_PATH)
    request = storage_transfer_v1.RunTransferJobRequest(
        job_name="transferJobs/OPI14932910461025069603",  # need to pass this in initiation event
        project_id="charged-scholar-399420",
    )
    operation = await client.run_transfer_job(request=request)
    return operation.operation.name


async def hello(request):
    return web.Response(text="Hello, world")


async def count_en(request):
    data = await request.json()
    print(data)
    try:
        words_list_filename = data['words_list_filename']
        results_filename = data['results_filename']
        transfer_operation_name = data['transfer_operation_name']
        callback_broker = data['callback_broker_url']
        callback_key = data['callback_key']
    except (KeyError, TypeError, ValueError) as e:
        raise web.HTTPBadRequest(
            text='Missing required values') from e

    # wait for file words_list_filename to be transfered
    wait_on_transfer_job(transfer_operation_name)

    # read words list, filter them and count
    data = read_blob(WORDS_LIST_BUCKET, f'words-list/{words_list_filename}')
    words_list = data['words_list']

    with open(REF_DICT) as f:
        dict_words = f.read().split(' ')

    filtered_words = [w for w in words_list if w not in dict_words]
    write_blob(RESULTS_BUCKET, f'results/{results_filename}', {"en_words": len(filtered_words)})

    # trigger results transfer job
    operation_name = await trigger_results_transfer_job()
    
    # version 2 additions
    wait_on_transfer_job(transfer_operation_name)

    try:
        # fire callback event
        async with ClientSession().post(
            callback_broker,
            json={
                'results_filename': results_filename,
                'key': callback_key
            },
            headers={
                'Content-Type': 'application/json',
                "Ce-Id": f"event_{get_random_str()}",
                "Ce-Specversion": "1.0",
                "Ce-Type": "count-en",
                "Ce-Source": "local-dag-count-en-words",
                "Ce-Appversion": "2.0.0",
                "Ce-callback-key": callback_key
            }
        ) as resp:
            status = resp.status
            response_json = await resp.json()
            print(f"Fired callback {status} {response_json}")
    except Exception as ex:
        print(f"Got error while firing callback {ex}")
    # end version 2 additions

    return web.Response(text=json.dumps({"results_filename": results_filename, "results_transfer_job_name": operation_name}))


app.add_routes([web.post('/count-en/', count_en)])
app.add_routes([web.post('/count-en', count_en)])
app.add_routes([web.get('/count-en/', count_en)])
app.add_routes([web.get('/count-en', count_en)])
app.add_routes([web.get('/', hello)])
web.run_app(app, port=8083)
