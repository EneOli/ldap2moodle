import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import moodle
import json

KEY = 'REPLACE_ME'
URL = 'REPLACE_ME'
ENDPOINT = '/webservice/rest/server.php'

m = moodle.Moodle(URL + ENDPOINT, KEY)

user_updates = 0

with open('user_dump.json', 'r') as userfile:
    users = json.load(userfile)['users']
    newUsers = m.users_get({'key': 'auth', 'value': 'ldap'})['users']
    for user in users:
        if "linux.lokal" not in user["email"]:
            for nUser in newUsers:
                if nUser['username'] == user['username']:
                    if 'linux.lokal' not in nUser['email']:
                        break
                    user_updates = user_updates + 1
                    print('Update user: ', user['username'], ' <', user['email'], '>')
                    m.users_update([{'id': nUser['id'], 'email': user['email']}])

print('=== DONE, edited ' + str(user_updates) + ' users ===')
