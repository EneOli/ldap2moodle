# ldap2moodle

Sync LDAP users and classes from linuxmuster.net to a Moodle installation using its REST api.
## Getting Started

These instructions will get you a copy of the project up and running. Please note that although this script works, it is still in an early development state, must be adopted to your needs and should be
used with care. Please make a backup of your moodle instance before running the script.

### Prerequisites

```
python3 (!) with pip available ( a normal installation)
```

### Installing

To get a copy of the project, follow these steps

```
Clone the project

cd into project folder and pip install -r requirements.txt
```

## Run

To run the script, a teachers.csv needs to be in the project root.
It contains information about the teachers and classes they are teaching:

```
6f;Petra Mustermann;DE
11;John Doe;1en3
12;Max Meyer;MA512
```
Please note that at this point the script is tightly connected with our course naming system, so if you have other naming conventions, you need to modify the regex.

To run the script, a moodle api token is required. Create one according to [these instructions](https://moodle.org/mod/forum/discuss.php?d=319039)
The following functions are needed:
 - core_course_create_categories
 - core_course_get_categories
 - core_course_create_courses
 - core_course_get_courses_by_field
 - core_user_create_users
 - enrol_manual_enrol_users
 - core_course_update_categories

Also at this point the script needs to be modified to access the api endpoint and ldap server. Open it in your favourite code editor and change the following:
````
role_teacher = 'editingteacher'  # the script needs to know the role_id for teacher
role_student = 'student'  # and student for enroling users to courses

cat_students = 'Schüler'  # names for the basic categories in moodle
cat_teachers = 'Lehrer'

rid_students = 5  # to enrol users to a course, the global role id is
rid_teachers = 3  # needed - in a normal installation these values should be fine

teachersroom = 'teachers'  # Name of the teachers course

oberstufe = ['11', '12']

unterstufe_preset = "unterstufe_preset" # preset for classes 5 - 10

# machine accounts, adminsitrators, ... will be filtered by gecos data field (maybe there is a better way?)
gecos_exclude = ['admin']

# the key, base-url and endpoint for the moodle REST api
KEY = 'REPLACE_ME'
URL = 'https://moodle.myschool.de'
ENDPOINT = '/webservice/rest/server.php' # should be ok

# ldap settings
ldap_server = 'ldap://ldap.myschool.de'
ldap_binddn = ''  # not used so far
ldap_bindpw = ''  # anonymous bind
ldap_basedn = 'ou=accounts, dc=linux, dc=local'
````


Create a course named unterstufe_preset and fill it with topics, files, etc. This is the preset for classes 5 - 10. You might also want to set it invisible.
## Contributing

Contributions are very welcome. Please create issues and pull requests so we can improve this script. But also please note that there is no fixed time I'm working on this.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* **Thomas Schröder (thoschi)** - *Initial work* - [linuxmuster profile](https://ask.linuxmuster.net/u/thoschi) - [original source code](https://gitlab.com/thoschi/lml2moodle)


