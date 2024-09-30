#!/usr/bin/env python

import datetime
import logging
import os
from pathlib import Path

import requests
from peewee import CharField, DateTimeField, Model, SqliteDatabase
from requests_html import HTMLSession


def get_remote_resource_names() -> list[str]:
    session = HTMLSession()
    url = "https://docs.datadoghq.com/infrastructure/resource_catalog/schema/"
    logging.info(f"Requesting data from {url}...")
    return sorted(
        [
            e.text
            for e in session.get(url).html.find("#mainContent", first=True).find("code")
        ]
    )


if __name__ == "__main__":
    logging.basicConfig(level="INFO")

    local_db = Path.home() / "datadog-schema.db"
    logging.info(f"Using database found at {local_db}.")
    db = SqliteDatabase(local_db)

    class Resource(Model):
        name = CharField(unique=True)
        provider = CharField()
        created_date = DateTimeField(default=datetime.datetime.now)

        class Meta:
            database = db

    db.connect()
    db.create_tables([Resource])

    remote_resource_name_set = set(get_remote_resource_names())
    logging.info(f"Found remote resources {remote_resource_name_set}.")
    local_resource_name_set = set([r.name for r in Resource.select()])
    logging.info(f"Found local resources {local_resource_name_set}.")
    added_resource_name_set = sorted(
        remote_resource_name_set.difference(local_resource_name_set)
    )
    removed_resource_name_set = sorted(
        local_resource_name_set.difference(remote_resource_name_set)
    )

    with db.atomic() as txn:
        for resource_name in added_resource_name_set:
            provider = resource_name.split("_")[0]
            d = {"name": resource_name, "provider": provider}
            logging.info(f"Creating resource {d}...")
            r = Resource.create(**d)

        for resource_name in removed_resource_name_set:
            logging.info(f"Deleting resource with name={resource_name}...")
            Resource.get(Resource.name == resource_name).delete_instance()

    db.close()

    webhook_url = os.getenv("DEFAULT_SLACK_NOTIFICATIONS_WEBHOOK_URL")
    if webhook_url and (added_resource_name_set or removed_resource_name_set):
        output = "\n".join(
            [
                "New Datadog Resource Catalog Schema Changes!",
                "Added:",
                "\n".join(added_resource_name_set),
                "Removed:",
                "\n".join(removed_resource_name_set),
            ]
        )
        logging.debug(f"Result output:\n{output}")
        logging.info("Sending result output to Slack...")
        requests.post(
            webhook_url,
            json={"text": output},
        )
