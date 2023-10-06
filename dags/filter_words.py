import json
import string
import secrets
import requests
import os
from time import sleep

from google.cloud import storage, storage_transfer_v1
from airflow.decorators import dag, task
from pendulum import datetime as pendulum_datetime


REF_DICT = "/home/jane/Documents/airflow/dags/dict.txt"  # 'dict.txt'
WORDS_LIST_BUCKET = os.getenv("KN_POC_BUCKET_WORDSLIST", "river-sand")
RESULTS_BUCKET = os.getenv("KN_POC_BUCKET_RESULTS", "river-sand")
GCP_CREDS_PATH = "/home/jane/Documents/airflow/dags/gcp-creds.json"  # "gcp-creds.json"


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


def trigger_results_transfer_job(job_name_to_transfer_back, project_id):
    client = storage_transfer_v1.StorageTransferServiceClient.from_service_account_json(GCP_CREDS_PATH)
    request = storage_transfer_v1.RunTransferJobRequest(
        job_name=job_name_to_transfer_back,
        project_id=project_id,
    )
    operation = client.run_transfer_job(request=request)
    return operation.operation.name


default_args = {"start_date": pendulum_datetime(2023, 8, 29)}


@dag("filter_words", schedule=None, default_args=default_args, catchup=False)
def filter_words():

    @task
    def wait_on_transfer_job_task(*args, **kwargs):  # can be deferred operator which doesn't occupy the slot when waiting
        transfer_operation_name = kwargs['dag_run'].conf.get('transfer_operation_name')
        print(f"DAG conf: {kwargs['dag_run'].conf}")
        print(f"Operation name: {transfer_operation_name}")
        wait_on_transfer_job(transfer_operation_name)
    
    @task
    def filter_and_count_words(*args, **kwargs):
        words_list_filename = kwargs['dag_run'].conf.get('words_list_filename')
        results_filename = kwargs['dag_run'].conf.get('results_filename')

        data = read_blob(WORDS_LIST_BUCKET, f'words-list/{words_list_filename}')
        words_list = data['words_list']

        with open(REF_DICT) as f:
            dict_words = f.read().split(' ')

        filtered_words = [w for w in words_list if w not in dict_words]
        write_blob(RESULTS_BUCKET, f'results/{results_filename}', {"en_words": len(filtered_words)})
    
    @task
    def trigger_wait_on_transfer_back(*args, **kwargs): # can be deferred operator which doesn't occupy the slot when waiting
        job_name_to_transfer_back = kwargs['dag_run'].conf.get("incoming_job_name")
        project_id = kwargs['dag_run'].conf.get("project_id")

        # trigger results transfer job
        operation_name = trigger_results_transfer_job(job_name_to_transfer_back, project_id)
        wait_on_transfer_job(operation_name)
        return operation_name
    
    @task
    def send_callback_event(*args, **kwargs):  # this task can run always, regardless whether prev ones failed, and post status of dag run
        callback_broker = kwargs['dag_run'].conf.get('callback_broker', None)
        callback_key = kwargs['dag_run'].conf.get('callback_key', None)
        
        if not callback_broker or not callback_key:
            print('No callback provided')
            return
            
        try:
            # fire callback event
            resp = requests.post(
                callback_broker,
                json={
                    'status': 'good', # TODO get status of prev tasks in dag
                    'key': callback_key
                },
                headers={
                    'Content-Type': 'application/json',
                    "Ce-Id": f"event_callback_{callback_key}_{get_random_str()}",
                    "Ce-Specversion": "1.0",
                    "Ce-Type": "count-en",
                    "Ce-Source": "filter-words-dag",
                    "Ce-Appversion": "2.0.0",
                    "Ce-callbackkey": callback_key
                }
            )
            status = resp.status_code
            response_text = resp.content.decode()
            print(f"Fired callback, response: {status} {response_text}")
        except Exception as exc:
            print(f"Got error while firing callback {exc}")


    wait_on_transfer_job_task() >> filter_and_count_words() >> trigger_wait_on_transfer_back() >> send_callback_event()


filter_words()
