import re
import json

# Read the SQL-like markup from the file
with open('schema-markup.txt', 'r') as file:
    sql_markup = file.read()

print(sql_markup)

# Initialize the schema dictionary
schema = {"tables": {}}

# Regular expressions to match table definitions and columns
table_regex = re.compile(r'(\w+)\s*{([^}]*)}', re.MULTILINE)
column_regex = re.compile(r'(\w+)\s+(\w+)(\s+pk)?(\s*>\s*(\w+\.\w+))?', re.MULTILINE)

# Mapping from SQL-like types to JSON types
type_mapping = {
    "int": "Integer",
    "varchar": "String",
    "boolean": "Boolean",
    "float": "Float"
}

# Parse the SQL-like markup
for table_match in table_regex.finditer(sql_markup):
    table_name = table_match.group(1)
    columns_text = table_match.group(2)
    columns = {}
    foreign_keys = {}
    for column_match in column_regex.finditer(columns_text):
        column_name = column_match.group(1)
        column_type = type_mapping[column_match.group(2)]
        primary_key = bool(column_match.group(3))
        references = column_match.group(5)
        columns[column_name] = {"type": column_type}
        if primary_key:
            columns[column_name]["primary_key"] = True
        if references:
            foreign_keys[column_name] = {"references": references}
    schema["tables"][table_name] = {"columns": columns}
    if foreign_keys:
        schema["tables"][table_name]["foreign_keys"] = foreign_keys

# Write the schema to a JSON file
with open('schema.json', 'w') as file:
    json.dump(schema, file, indent=4)

print("Schema converted to JSON successfully.")