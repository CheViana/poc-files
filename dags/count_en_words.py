
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.email_operator import EmailOperator
from airflow.operators.bash import BashOperator
from airflow.decorators import dag, task
from pendulum import datetime
from collections import defaultdict
import json
import string
import secrets
import requests
import os
from google.cloud import storage_transfer_v1
from google.api_core.exceptions import AlreadyExists


BASE_PATH = os.getenv('KN_POC_HOME', '/home/jane/Documents/airflow')
# FILE_PATH = f'{BASE_PATH}/inputfiles/lorem.txt'
REF_DICT = f'{BASE_PATH}/textfiles/dict.txt'
RESULTS_PATH = BASE_PATH + '/results/results_{}.txt'
WORD_LIST_PATH = BASE_PATH + '/textfiles/words_list_{}.txt'
GCP_CREDS_PATH = f'{BASE_PATH}/dags/gcp-creds.json'

default_args = {"start_date": datetime(2023, 8, 29)}


@dag("count_en_words", schedule=None, default_args=default_args, catchup=False)  # description='Count English words in text', 
def count_en_words():

    def lines_gen(file_path):
        with open(file_path) as f:
            for line in f:
                yield line

    def get_random_str():
        return ''.join(
            secrets.choice(string.ascii_lowercase + string.digits) for i in range(8)
        )

    @task
    def create_words_list(*args, **kwargs):
        file_path = kwargs['dag_run'].conf.get('filepath')
        print(file_path)
        lines = lines_gen(file_path)
        words_set = set()
        for line in lines:
            if not line.strip():
                continue
            without_punct = line.translate(str.maketrans('', '', string.punctuation))
            words = [w.lower() for w in without_punct.split()]
            words_set |= set(words)
        
        random_str = get_random_str()
        words_list_path = WORD_LIST_PATH.format(random_str)
        results_path = RESULTS_PATH.format(random_str)

        with open(words_list_path, 'w') as f:
            json.dump({"words_list": list(words_set), "results_path": results_path}, f)

        return random_str

    @task
    def trigger_data_transfer(*args, **kwargs):

        response = requests.post(
            'http://localhost:8084/call-test-event?path=knative-eventing%2Fcount-en-broker',
        )
        response.raise_for_status()
        job_data = response.json()

        client = storage_transfer_v1.StorageTransferServiceClient.from_service_account_json(GCP_CREDS_PATH)
        request = storage_transfer_v1.RunTransferJobRequest(
            job_name=job_data["outgoing_job_name"],
            project_id=job_data["project_id"],
        )
        try:
            operation = client.run_transfer_job(request=request)
            print(operation.operation.name)
            return (operation.operation.name, job_data)
        except AlreadyExists:
            print('Transfer already running')
            # TODO get operation name?
        return (None, None)
    
    @task
    def invoke_remote_en_count(*args, **kwargs):
        task_instance = kwargs['ti']
        random_str = task_instance.xcom_pull(task_ids='create_words_list')
        results_filename = f'results_{random_str}.txt'
        words_list_filename = f'words_list_{random_str}.txt'
        operation_name, job_data = task_instance.xcom_pull(task_ids='trigger_data_transfer')
        ingress = job_data["ingress"]
        incoming_job_name = job_data["incoming_job_name"]
        project_id = job_data["project_id"]
        response = requests.post(
            f'http://{ingress}/knative-eventing/count-en-broker',
            json={
                "words_list_filename": words_list_filename,
                "results_filename": results_filename,
                "transfer_operation_name": operation_name,
                "callback_broker": "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/knative-eventing/fake-local-broker",
                "callback_key": random_str,
                "incoming_job_name": job_data["incoming_job_name"],
                "project_id": job_data["project_id"]
            },
            headers={
                'Content-Type': 'application/json',
                "Ce-Id": f"event_{random_str}",
                "Ce-Specversion": "1.0",
                "Ce-Type": "count-en",
                "Ce-Source": "local-dag-count-en-words",
                "Ce-Appversion": kwargs['dag_run'].conf.get('appversion', "1.0.0"),
            }
        )
        print(response.content)
        response.raise_for_status()

    @task
    def echo_results(*args, **kwargs):
        task_instance = kwargs['ti']
        random_str = task_instance.xcom_pull(task_ids='create_words_list')
        filename = RESULTS_PATH.format(random_str)
        print(f'Reading results: {filename}')
        with open(filename, 'r') as f:
            results = f.read()
            print(results)
        return str(results)

    # instead of sense_the_results:
    # listen to kafka topic (the one in fake-local-broker) for msg with callback_key and matching appversion
    sense_the_results = FileSensor(  # can be defered trigger and not occupy the slot
        task_id='sense_the_results',
        filepath=RESULTS_PATH.format("{{ task_instance.xcom_pull(task_ids='create_words_list') }}"),
        poke_interval=3
    )

    @task
    def get_email(*args, **kwargs):
        return kwargs['dag_run'].conf.get('email')

    # send_email = EmailOperator( 
    #     task_id='send_email', 
    #     to="{{ task_instance.xcom_pull(task_ids='get_email') }}", 
    #     subject='Words counted', 
    #     html_content="{{ task_instance.xcom_pull(task_ids='echo_results') }}", 
    # )

    # trigger_file_transfer = BashOperator(
    #     task_id="trigger_file_transfer",
    #     bash_command=f"gcloud transfer jobs run {LOCAL_TO_REMOTE_JOB_NAME}",
    # )

    create_words_list() >> trigger_data_transfer() >> invoke_remote_en_count() >> sense_the_results >> echo_results() >> get_email() # >> send_email

count_en_words()
