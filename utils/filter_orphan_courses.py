import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import moodle

# needs
# * core_course_get_courses
# * core_enrol_get_enrolled_users

KEY = 'REPLACE_ME'
URL = 'REPLACE_ME'
ENDPOINT = '/webservice/rest/server.php'

m = moodle.Moodle(URL + ENDPOINT, KEY)

result = m.courses_get()

for course in result:
    users = m.course_get_enroled_user(course['id'])
    teacher = False
    for user in users:
        if user['roles'] and user['roles'][0]['shortname'] == 'editingteacher':
            teacher = True
            break
    if not teacher:
        print(course['displayname'])
