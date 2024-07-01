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
from zoneinfo import ZoneInfo
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
                "event",
                "recordtime",
                "remotehost",
                "remoteport",
                "pid",
                "dbname",
                "username",
                "authmethod",
                "duration",
                "sslversion",
                "sslcipher",
                "mtu",
                "sslcompression",
                "sslexpansion",
                "iamauthguid",
                "application_name",
                "date",
                "hour",
            ]
        )

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
                        "event",
                        "recordtime",
                        "remotehost",
                        "remoteport",
                        "pid",
                        "dbname",
                        "username",
                        "authmethod",
                        "duration",
                        "sslversion",
                        "sslcipher",
                        "mtu",
                        "sslcompression",
                        "sslexpansion",
                        "iamauthguid",
                        "application_name",
                        "date",
                        "hour",
                    ]
                )

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

                for i in range(message_df.shape[0]):
                    timestamp = message_df.at[i, "timestamp"]

                    t = timestamp / 1000

                    gm = gmtime(t)
                    local = localtime(t)

                    time_format = "%Y-%m-%d %H:%M:%S %Z"

                    gm_time = strftime(time_format, gm)
                    # local_time = strftime(time_format, local)

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

                    # print(message)

                    s_message = message.split("|")

                    recordtime_string = s_message[1]
                    recordtime_dt = datetime.strptime(
                        recordtime_string, "%a, %d %b %Y %H:%M:%S:%f"
                    )
                    dt_with_tz = recordtime_dt.replace(tzinfo=ZoneInfo("UTC"))
                    formatted_recordtime = (
                        dt_with_tz.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"
                    )

                    message_df.at[i, "event"] = s_message[0]
                    message_df.at[i, "recordtime"] = formatted_recordtime
                    message_df.at[i, "remotehost"] = s_message[2]
                    message_df.at[i, "remoteport"] = s_message[3]
                    message_df.at[i, "pid"] = s_message[4]
                    message_df.at[i, "dbname"] = s_message[5]
                    message_df.at[i, "username"] = s_message[6]
                    message_df.at[i, "authmethod"] = s_message[7]
                    message_df.at[i, "duration"] = s_message[8]
                    message_df.at[i, "sslversion"] = s_message[9]
                    message_df.at[i, "sslcipher"] = s_message[10]
                    message_df.at[i, "mtu"] = s_message[11]
                    message_df.at[i, "sslcompression"] = s_message[12]
                    message_df.at[i, "sslexpansion"] = s_message[13]
                    message_df.at[i, "iamauthguid"] = s_message[14]
                    message_df.at[i, "application_name"] = s_message[15]

                message_df["event"] = message_df["event"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["recordtime"] = message_df["recordtime"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["remotehost"] = message_df["remotehost"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["remoteport"] = message_df["remoteport"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["pid"] = message_df["pid"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["dbname"] = message_df["dbname"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["username"] = message_df["username"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["authmethod"] = message_df["authmethod"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["duration"] = message_df["duration"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["sslversion"] = message_df["sslversion"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["sslcipher"] = message_df["sslcipher"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["mtu"] = message_df["mtu"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["sslcompression"] = message_df["sslcompression"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["sslexpansion"] = message_df["sslexpansion"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["iamauthguid"] = message_df["iamauthguid"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
                message_df["application_name"] = message_df["application_name"].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )

                object_df = pd.concat([object_df, message_df])

            # end if
            # end of a message

        # end of an object(messages)

        df_log = object_df[
            [
                "id",
                "timestamp",
                "message",
                "localtime",
                "event",
                "recordtime",
                "remotehost",
                "remoteport",
                "pid",
                "dbname",
                "username",
                "authmethod",
                "duration",
                "sslversion",
                "sslcipher",
                "mtu",
                "sslcompression",
                "sslexpansion",
                "iamauthguid",
                "application_name",
                "date",
                "hour",
            ]
        ]

        # Write partitioned Parquet to S3
        # https://aws-sdk-pandas.readthedocs.io/en/stable/stubs/awswrangler.s3.to_parquet.html
        wr.s3.to_parquet(
            df=df_log,
            path="s3://redshiftauditlogs-partitioned-687423707850-ap-northeast-2/connectionlog/",
            dataset=True,
            database="redshiftauditlog",  # Athena/Glue database
            table="connectionlog",
            compression="gzip",
            partition_cols=["date", "hour"],
        )

    except Exception as e:
        print(e)

    # TODO implement
    # 'body': json.dumps(body_data_str4)
    return {"statusCode": 200, "body": object_key}
