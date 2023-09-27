
from airflow.contrib.sensors.file_sensor import FileSensor
from airflow.operators.bash import BashOperator
from airflow.decorators import dag, task
from pendulum import datetime
from collections import defaultdict
import json
import string
import secrets

FILE_PATH = '/home/jane/Documents/airflow/inputfiles/lorem.txt'
REF_DICT = '/home/jane/Documents/airflow/textfiles/dict.txt'
RESULTS_PATH = '/home/jane/Documents/airflow/results/results_{}.txt'
WORD_LIST_PATH = '/home/jane/Documents/airflow/textfiles/words_list_{}.txt'
LOCAL_TO_REMOTE_JOB_NAME = "OPI8437548298833795632"
default_args = {"start_date": datetime(2023, 8, 29)}


@dag("sense_file", schedule=None, default_args=default_args, catchup=False)  # description='Count English words in text', 
def sense_file():

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
        # print(f"DAG args {args} kwargs {kwargs}")
        file_path = kwargs['dag_run'].conf.get('filepath')
        # file_path = FILE_PATH
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

        return words_list_path
 
    @task
    def count_en_words(words_list_path):
        with open(words_list_path, "r") as f:
            data = json.load(f)

        words_list = data["words_list"]
        results_path = data["results_path"]

        with open(REF_DICT) as f:
            dict_words = f.read().split(' ')
        filtered_words = [w for w in words_list if w in dict_words]
        print(f"Words count: {len(words_list)}, en words count: {len(filtered_words)}")
        with open(results_path, 'w') as f:
            json.dump({"en_words": len(filtered_words)}, f)
        
        return results_path

    @task
    def echo_results(*args, **kwargs):
        task_instance = kwargs['ti']
        #filename = task_instance.xcom_pull(task_ids='count_en_words')
        filename = RESULTS_PATH.format('2342sd')
        print(f'Reading results: {filename}')
        with open(filename, 'r') as f:
            print(f.read())

    sense_the_results = FileSensor(  # can be defered trigger and not occupy the slot
        task_id='sense_the_results',
        #filepath="{{ task_instance.xcom_pull(task_ids='count_en_words') }}",
        filepath=RESULTS_PATH.format('2342sd'),
        poke_interval=3
    )

    # trigger_file_transfer = BashOperator(
    #     task_id="trigger_file_transfer",
    #     bash_command=f"gcloud transfer jobs run {LOCAL_TO_REMOTE_JOB_NAME}",
    # )

    # count_en_words(create_words_list()) >> trigger_file_transfer >> 
    
    sense_the_results >> echo_results()

sense_file()
