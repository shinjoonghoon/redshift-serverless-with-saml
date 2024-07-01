import os

import boto3
import gzip
import json
import re

from io import BytesIO
from io import StringIO

import numpy as np
import pandas as pd
from time import localtime, strftime, gmtime
from glob import glob

import awswrangler as wr

from datetime import datetime
import pytz
import time

s3_client = boto3.client("s3")
s3 = boto3.resource("s3")


def transformLogEvent(log_event, log_event_type):
    """Transform each log event.

    The default implementation below just extracts the message and appends a newline to it.

    Args:
    log_event (dict): The original log event. Structure is {"id": str, "timestamp": long, "message": str}

    Returns:
    str: The transformed log event.
    """
    if log_event_type == "id":
        return log_event["id"] + "\n"
    elif log_event_type == "timestamp":
        return str(log_event["timestamp"]) + "\n"
    elif log_event_type == "message":
        return log_event["message"] + "\n"


def lambda_handler(event, context):

    try:
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        object_key = event["Records"][0]["s3"]["object"]["key"]

        response = s3_client.get_object(Bucket=bucket, Key=object_key)

        body = response["Body"].read()

        body_data_str = body.decode("ASCII")

        body_data_str2 = re.sub("^", "[", body_data_str)
        body_data_str3 = re.sub("$", "]", body_data_str2)
        body_data_str4 = re.sub(
            '\\}\\{"messageType"', '},{"messageType"', body_data_str3
        )

        messages_per_obj = json.loads(body_data_str4)

        # https://docs.aws.amazon.com/ko_kr/AmazonCloudWatch/latest/logs/ValidateLogEventFlow.html
        object_df = pd.DataFrame(
            columns=[
                "message",
                "id",
                "timestamp",
                "localtime",
                "recordtime",
                "db",
                "user",
                "pid",
                "userid",
                "xid",
                "log",
                "date",
                "hour",
            ]
        )

        # message_cnt = 0

        for m in messages_per_obj:

            # message_cnt += 1

            # print(type(m)) # <class 'dict'>
            # print(m['messageType'])
            # print(type(m['messageType'])) # <class 'str'>
            # print(type(m['logEvents'])) # <class 'list'>

            messageType = m["messageType"]
            logEvents = m["logEvents"]

            if messageType == "CONTROL_MESSAGE":
                print(messageType)
                continue

            else:

                message_df = pd.DataFrame(
                    columns=[
                        "message",
                        "id",
                        "timestamp",
                        "localtime",
                        "recordtime",
                        "db",
                        "user",
                        "pid",
                        "userid",
                        "xid",
                        "log",
                        "date",
                        "hour",
                    ]
                )

                # object_df = pd.DataFrame()

                id_joinedData = "".join([transformLogEvent(e, "id") for e in logEvents])
                timestamp_joinedData = "".join(
                    [transformLogEvent(e, "timestamp") for e in logEvents]
                )
                message_joinedData = "".join(
                    [transformLogEvent(e, "message") for e in logEvents]
                )

                message_df["id"] = pd.read_csv(
                    StringIO(id_joinedData), sep="\r\n", header=None, engine="python"
                )
                message_df["timestamp"] = pd.read_csv(
                    StringIO(timestamp_joinedData),
                    sep="\r\n",
                    header=None,
                    engine="python",
                )
                message_df["message"] = pd.read_csv(
                    StringIO(message_joinedData),
                    sep="\r\n",
                    header=None,
                    engine="python",
                )

                tmp_recordtime = ""
                tmp_db = ""
                tmp_user = ""
                tmp_userid = ""
                tmp_pid = ""
                tmp_xid = ""

                for i in range(message_df.shape[0]):
                    timestamp = message_df.at[i, "timestamp"]

                    t = timestamp / 1000

                    gm = gmtime(t)
                    # local = localtime(t)

                    time_format = "%Y-%m-%d %H:%M:%S %Z"

                    gm_time = strftime(time_format, gm)

                    gm_datetime = datetime.strptime(gm_time, time_format).replace(
                        tzinfo=pytz.UTC
                    )
                    kst_timezone = pytz.timezone("Asia/Seoul")
                    kst_datetime = gm_datetime.astimezone(kst_timezone)
                    local_time = kst_datetime.strftime(time_format)
                    local_time_tuple = kst_datetime.timetuple()

                    formatted_date = time.strftime("%Y/%m/%d", local_time_tuple)
                    formatted_hour = time.strftime("%H", local_time_tuple)

                    message_df.at[i, "localtime"] = local_time
                    message_df.at[i, "date"] = formatted_date
                    message_df.at[i, "hour"] = formatted_hour

                    message = message_df.at[i, "message"]

                    recordtime = re.search(r"^\'(.*?)\[", message)

                    if recordtime is not None:
                        tmp_recordtime = recordtime.group(1)

                    message_df.at[i, "recordtime"] = tmp_recordtime

                    message_without_recordtime = re.search(
                        r"\[(.*)\]\'\sLOG:\s(.*)", message
                    )

                    if message_without_recordtime is not None:
                        square_bracket = message_without_recordtime.group(1)
                        log = message_without_recordtime.group(2)

                        message_df.at[i, "log"] = log

                        elements_in_square_bracket = re.search(
                            r"\s+db=(.*?)\s+user=(.*?)\s+pid=(.*?)\s+userid=(.*?)\s+xid=(.*?)\s",
                            square_bracket,
                        )

                        tmp_db = elements_in_square_bracket.group(1)
                        tmp_user = elements_in_square_bracket.group(2)
                        tmp_pid = elements_in_square_bracket.group(3)
                        tmp_userid = elements_in_square_bracket.group(4)
                        tmp_xid = elements_in_square_bracket.group(5)

                    else:
                        message_df.at[i, "log"] = message

                    message_df.at[i, "db"] = tmp_db
                    message_df.at[i, "user"] = tmp_user
                    message_df.at[i, "pid"] = tmp_pid
                    message_df.at[i, "userid"] = tmp_userid
                    message_df.at[i, "xid"] = tmp_xid

                message_df["recordtime"] = message_df["recordtime"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )

                object_df = pd.concat([object_df, message_df])
            # end if
            # end of a message

        df_log = object_df[
            [
                "id",
                "timestamp",
                "message",
                "localtime",
                "recordtime",
                "db",
                "user",
                "pid",
                "userid",
                "xid",
                "log",
                "date",
                "hour",
            ]
        ]

        # Write partitioned Parquet to S3
        wr.s3.to_parquet(
            df=df_log,
            path="s3://redshiftauditlogs-partitioned-687423707850-ap-northeast-2/useractivitylog/",
            dataset=True,
            compression="gzip",
            database="redshiftauditlog",  # Athena/Glue database
            table="useractivitylog",
            partition_cols=["userid", "date", "hour"],
        )

    except Exception as e:
        print(e)

    # TODO implement
    # 'body': json.dumps(body_data_str4)
    return {"statusCode": 200, "body": object_key}
