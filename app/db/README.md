Attempting to define the schema once for database generation, data import scripts and model views and validation. 

The API requires `schema.json` which represents the postgres database definition sql in json format. It is generated from `schema-markup.txt` by

```
python sql_to_json.py
```

