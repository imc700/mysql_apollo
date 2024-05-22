import json
import os
import threading
import time
import pymysql
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from datetime import datetime, timedelta

from pymysql import Connection


class AppConfig(BaseSettings):
    model_config = ConfigDict(extra='allow')

    a1: str = '1'
    a2: str = '2'


class MysqlApollo:
    def __init__(self):
        self.connection = self.connect_to_database()
        self.threading_start_time = datetime.now() - timedelta(hours=8)
        heartbeat = threading.Thread(target=self._heartBeat)
        heartbeat.daemon = True
        heartbeat.start()

    def connect_to_database(self) -> Connection:
        timeout = 100
        return pymysql.connect(
            charset="utf8mb4",
            connect_timeout=timeout,
            cursorclass=pymysql.cursors.DictCursor,
            host=os.getenv('host'),
            port=os.getenv('port'),
            user=os.getenv('user'),
            password=os.getenv('password'),
            db=os.getenv('db'),
            read_timeout=timeout,
            write_timeout=timeout,
            autocommit=False
        )

    def _heartBeat(self):
        while True:
            time.sleep(10)  # wait 10s
            if not self.connection or self.connection.open is False:
                self.connect_to_database()
            if self._do_heartBeat():
                print(f'change_listener.............')
                global configs
                configs = self.get_configs()
                self.threading_start_time = datetime.now() - timedelta(hours=8)

    def _do_heartBeat(self) -> int:
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                f"""select count(1) as cc from t_apollo_config where project_name='{os.getenv("project_name").strip()}' """
                f"""and env='{os.getenv("env", "dev").strip()}' """
                f"""and created_time>'{self.threading_start_time}' """)
            result = cursor.fetchone()
            if result:
                return result['cc']
        finally:
            self.connection.commit()

    def get_configs(self) -> AppConfig:
        # 读取MySQL,获取配置
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                f"""select * from t_apollo_config where project_name='{os.getenv("project_name").strip()}' """
                f"""and env='{os.getenv("env", "dev").strip()}' order by created_time desc limit 1""")
            result = cursor.fetchone()
            print(f'result: {result}')
            if result:
                json_conf = result['content']
                print(f'json_conf: {json_conf}')
                apollo_dic = json.loads(json_conf)
                return AppConfig(**apollo_dic)
        finally:
            self.connection.commit()


mysql_apollo = MysqlApollo()
configs = mysql_apollo.get_configs()

if __name__ == '__main__':
    while True:
        print(configs)
        time.sleep(10)
