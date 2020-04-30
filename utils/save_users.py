import os
import sys
import inspect
import json

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import moodle

KEY = 'REPLACE_ME'
URL = 'REPLACE_ME'
ENDPOINT = '/webservice/rest/server.php'

m = moodle.Moodle(URL + ENDPOINT, KEY)

result = m.users_get({'key': 'auth', 'value': 'ldap'})

with open('user_dump.json', "w") as file:
    file.write(json.dumps(result))
