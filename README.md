This microservice automates the documentation of notifications on confluence when the node is using hardcoded notifications introduced by microservice: https://github.com/sesam-community/node-notification-handler

```{
  "_id": "confluence-poster",
  "type": "system:microservice",
  "docker": {
    "environment": {
      "CONFLUENCE_PASSWORD": "",
      "CONFLUENCE_USERNAME": "",
      "JWT": "",
      "LOG_LEVEL": "DEBUG",
      "NODE_URL": "https://……sesam.cloud",
      "PAGE_ID": "<confluence_page_id_to_update>"
    },
    "image": "gabbebabbe/confluence_poster",
    "port": 5000
  },
  "verify_ssl": true
}
``` 

It creates a table with 1 column for pipename and 1 for each notification type.
Notification type column is filled with notification description value.