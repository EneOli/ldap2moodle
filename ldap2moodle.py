# this script reads user and class information from an linuxmuster.net ldap
# and uses the moodle REST-API to create courses and enrols the users to the courses
# this is meant as a blueprint for the workflow and can easily be adopted

# run this script from any machine having ldap access to the ldap and
# web access to the moodle installation

# part one - read the user from linuxmuster.net-LDAP
# part two - write the structure to moodle

# first go to https://<your-moodle-address>/admin/category.php?category=webservicesettings
# you need to create a user/token for the functions used beneath
# - core_course_create_categories
# - core_course_get_categories
# - core_course_create_courses
# - core_course_get_courses_by_field
# - core_user_create_users
# - enrol_manual_enrol_users
# - core_course_update_categories

# do NOT do this to an existing moodle with courses that might conflict with
# the ones the script tries to create - this is meant for an innocent, new moodle
# and has not yet been tested at all!!
# !!!!!!!!! you have been warned !!!!!!!!!!!!!!!!!!!


# api documentation is here: https://<your-moodle-address>/admin/webservice/documentation.php

import sys
import ldap as pythonLdap
import re
import requests
import csv
import datetime

role_teacher = 'editingteacher'  # the script needs to know the role_id for teacher
role_student = 'student'  # and student for enroling users to courses

cat_students = 'Schüler'  # names for the basic categories in moodle
cat_teachers = 'Lehrer'

rid_students = 5  # to enrol users to a course, the global role id is
rid_teachers = 3  # needed - there seems to be no rest-ish way to get it

teachersroom = 'teachers'  # well... its quite clear, isn't it?

oberstufe = ['11', '12']

unterstufe_preset = "unterstufe_preset"

# machine accounts, adminsitrators, ... will be filtered by gecos data field (maybe there is a better way?)
gecos_exclude = ['admin 01', 'Programm Administrator', 'Web Administrator', 'Administrator', 'administrator',
                 'LINBO Administrator', 'ExamAccount']

# the key, base-url and endpoint for the moodle REST api
KEY = 'EDIT_ME'
URL = 'https://moodle.myschool.de'
ENDPOINT = '/webservice/rest/server.php'

ldap_server = 'ldap://ldap.myschool.de'
ldap_binddn = ''  # not used so far
ldap_bindpw = ''  # anonymous bind
ldap_basedn = 'EDIT_ME'

prefix_courses_jg = 'Jahrgang '


# -----------------------------------------------------------------


class LdapUser:
    def __init__(self, uid, sn, givenName, mail, cl):
        self.uid = str(uid)
        self.sn = str(sn)
        self.givenName = str(givenName)
        self.mail = str(mail)
        self.cl = str(cl)
        self.moodleId = None
        self.classTrainer = None


def getclassgroup(name):
    g = re.match('.*?([0-9]+)', name)
    if g is None:
        if name == 'teachers':
            return cat_teachers
        else:
            return cat_students
    else:
        return g.group(0)


def getfachbereichgroup(fachberiech, name):
    g = re.match('.*?([0-9]+)', name)
    if g is None:
        if name == 'teachers':
            return fachberiech + ' ' + cat_teachers
        else:
            return fachberiech + ' ' + cat_students
    else:
        return fachberiech + ' ' + g.group(0)


def getLdapUsers():
    """ reads the linuxmuster.net users from the server ldap """
    ldap = pythonLdap.initialize(ldap_server)  # initialize the ldap object
    basedn = ldap_basedn
    searchFilter = "(objectclass=person)"
    searchAttribute = []  # TODO: change this after testing
    searchScope = pythonLdap.SCOPE_SUBTREE  # scope entire subtree
    # ldap connect
    try:
        pythonLdap.set_option(pythonLdap.OPT_X_TLS_REQUIRE_CERT, pythonLdap.OPT_X_TLS_NEVER)  # ssl cert ignore
        ldap.protocol_version = pythonLdap.VERSION3
        ldap.simple_bind_s()
    except pythonLdap.INVALID_CREDENTIALS:
        print("Username or password is incorrect.")
        sys.exit(0)
    except pythonLdap.LDAPError as e:  # ldap bind failure
        if type(e['message']) == dict and 'desc' in e['message']:
            print(e['message']['desc'])
        else:
            print(e)
        sys.exit(0)

    result_set = []
    try:
        ldap_result_id = ldap.search(basedn, searchScope, searchFilter, searchAttribute)
        while True:
            result_type, result_data = ldap.result(ldap_result_id, 0)
            if result_data == []:
                break
            else:
                if result_type == pythonLdap.RES_SEARCH_ENTRY:
                    a, d = result_data[0]
                    # filter the admin-, exam- and machine-accounts
                    if d['gecos'][0].decode() not in gecos_exclude:
                        uid = d['uid'][0].decode()
                        sn = d['sn'][0].decode()
                        givenName = d['givenName'][0].decode()
                        mail = d['mail'][0].decode()
                        homeDirectory = d['homeDirectory'][0].decode().split(
                            '/')  # use 'home directory' for getting the class
                        if homeDirectory[2] == 'teachers':
                            cl = 'teachers'
                        elif homeDirectory[2] == 'students':
                            cl = homeDirectory[3]
                        else:
                            cl = False
                        result_set.append(LdapUser(uid, sn, givenName, mail, cl))
                        print(givenName + ' ' + sn + ' (' + uid + ') ' + ' <' + mail + '> - ' + str(cl))
    except pythonLdap.LDAPError as e:
        print(e)
    ldap.unbind_s()

    return result_set


ldapusers = getLdapUsers()  # get all user


class MoodleRole:
    def __init__(self, id, name):
        self.id = id
        self.name = name


def rest_api_parameters(in_args, prefix='', out_dict=None):
    """Transform dictionary/array structure to a flat dictionary, with key names defining the structure. """
    if out_dict is None:
        out_dict = {}
    if not type(in_args) in (list, dict):
        out_dict[prefix] = in_args
        return out_dict
    if prefix == '':
        prefix = prefix + '{0}'
    else:
        prefix = prefix + '[{0}]'
    if type(in_args) == list:
        for idx, item in enumerate(in_args):
            rest_api_parameters(item, prefix.format(idx), out_dict)
    elif type(in_args) == dict:
        for key, item in in_args.items():
            rest_api_parameters(item, prefix.format(key), out_dict)
    return out_dict


def call(fname, **kwargs):
    """Calls moodle API function with function name fname and keyword arguments. """
    parameters = rest_api_parameters(kwargs)
    parameters.update({"wstoken": KEY, 'moodlewsrestformat': 'json', "wsfunction": fname})

    import json
    f = open('params.txt', 'w')
    f.write(json.dumps(parameters))
    f.close()

    response = requests.post(URL + ENDPOINT, data=parameters).json()
    if type(response) == dict and response.get('exception'):
        raise SystemError("Error calling Moodle API\n", response)
    return response


def category_create(name, parentid, idnumber=None):
    if idnumber is None:
        idnumber = name.lower()
    """ Create Categories with 'name' and 'parentid' """
    return call('core_course_create_categories',
                categories=[{'name': name, 'parent': parentid, 'idnumber': idnumber}])


def category_get_id(name):
    """ get the id of a given category """

    res = call('core_course_get_categories', criteria=[{'key': 'name', 'value': name.lower()}])
    if res != []:
        res = [x for x in res if x['name'] == name]
        return res[0]['id']
    else:
        try:
            return category_get_id(cat_students)
        except:
            return None


def category_get_id_by_idnumber(idnumber):
    """ get the id of a given category """

    res = call('core_course_get_categories', criteria=[{'key': 'idnumber', 'value': idnumber}])
    if res != []:
        res = [x for x in res if x['idnumber'] == idnumber]
        return res[0]['id']
    else:
        try:
            return category_get_id(cat_students)
        except:
            return None


def course_create(name, categoryid, displayname=None):
    """ create a course with name and category-id """
    if displayname is None:
        course = {'fullname': name, 'shortname': name, 'categoryid': categoryid}
    else:
        course = {'fullname': name, 'shortname': name, 'categoryid': categoryid, 'name': displayname}
    return call('core_course_create_courses', courses=[course])


def course_create_from_preset(preset_course_id, fullname, shortname, category_id, idnumber=None):
    id = call('core_course_duplicate_course', courseid=preset_course_id, fullname=fullname, shortname=shortname,
              categoryid=category_id)['id']

    if idnumber is not None:
        call('core_course_update_courses', courses=[{'id': id, 'idnumber': idnumber, 'categoryid': categoryid}])


def course_get_id(name):
    """ returns course id or None"""
    crs_list = call('core_course_get_courses_by_field', field='shortname', value=name)['courses']
    if len(crs_list) == 0:
        print(f'No course found with shortname {name}!')
    elif len(crs_list) == 1:
        return crs_list[0]['id']
    else:
        print(f'Shortname {name} not unique. There are {len(crs_list)} courses with this shortname.')
    return None


def users_create(userlist):
    """ Create moodle-user from a list of ldap-users """
    users = []
    for u in userlist:
        user = {
            'username': u.uid,
            'firstname': u.givenName,
            'lastname': u.sn,
            'email': u.mail,
            'auth': 'ldap'
        }
        users.append(user)
    return call('core_user_create_users', users=users)


def enrol_users(users):
    """ manually enrols users to a course """
    with open('teachers.csv') as teacherfile:
        teachers = list(csv.reader(teacherfile, delimiter=';'))
        musers = []
        for u in users:
            muser = {}
            if u.cl == 'teachers':
                muser['roleid'] = rid_teachers
            else:
                muser['roleid'] = rid_students

            muser['userid'] = u.moodleId
            muser['courseid'] = course_get_id(u.cl)
            if muser['courseid'] is None:
                continue
            musers.append(muser)

        if len(musers) > 0:
            call('enrol_manual_enrol_users', enrolments=musers)


def enrol_trainers(trainers):
    """ manually enrols users to a course """
    print('enrolling teachers...')
    mtrainers = []
    for t in trainers:
        print(t.classTrainer)
        for course in t.classTrainer:
            print('in courses')
            print(course)
            mtrainer = {}
            if t.cl == 'teachers':
                mtrainer['roleid'] = rid_teachers
            else:
                RuntimeError('student would be teacher!')

            mtrainer['userid'] = t.moodleId
            mtrainer['courseid'] = course_get_id(course)
            if mtrainer['courseid'] is None:
                continue
            mtrainers.append(mtrainer)
    print(mtrainers)

    if len(mtrainers) > 0:
        call('enrol_manual_enrol_users', enrolments=mtrainers)


def get_category_id_name(cl):
    if getclassgroup(cl) == cat_students or getclassgroup(cl) == cat_teachers:
        return cl
    jg = int(getclassgroup(cl))
    jg = jg - 5
    year = datetime.datetime.now().year
    year = year - jg
    return 'jg' + str(year)


def get_course_id_name(cl):
    if getclassgroup(cl) == cat_students or getclassgroup(cl) == cat_teachers:
        return cl
    letter = re.match('.*?([A-z]+)', cl).group(1)
    jg = int(getclassgroup(cl))
    jg = jg - 5
    year = datetime.datetime.now().year
    year = year - jg
    return 'jg' + str(year) + '_' + letter


# create two main categories in moodle ('Schüler' and 'Lehrer')

for cn in [cat_teachers, cat_students]:
    print("* create basic category %s" % cn)
    category_create(cn, 0)


# create the classgroup-categories

def convertInt(s):
    try:
        match = next((x for x in oberstufe if x in str(s)), False)
        if match:
            s = match
        int(s)
        return int(s)
    except ValueError:
        return s


sorted_classes = list(set([convertInt((getclassgroup(u.cl))) for u in ldapusers if getclassgroup(u.cl) != "root"]))
print(sorted_classes)

sorted_classes = sorted([s for s in sorted_classes if s != cat_students and s != cat_teachers])
print(sorted_classes)

for cg in [str(s) for s in sorted_classes]:
    categoryid = category_get_id(cat_students)
    print(cat_students)
    print("* create subcategory", cg, 'in parent', categoryid)
    category_create(prefix_courses_jg + cg, categoryid, get_category_id_name(cg))

# create the courses in the classgroup-categories (and a teachers course in teachers category)
# every course that is not in category teachers OR any know subcategory will be in students subcat.
single = sorted(set([u.cl for u in ldapusers if u.cl != 'False' and u.cl != 'jg-11' and u.cl != 'jg-12']))
for c in single:
    if c == "teachers":
        categoryid = category_get_id(cat_teachers)
        coursename = teachersroom
        print("* create course %s in category %s (%d)" % (c, prefix_courses_jg + getclassgroup(c), categoryid))
        course_create(coursename, categoryid)
    else:
        print(get_category_id_name(c))
        categoryid = category_get_id(prefix_courses_jg + getclassgroup(c))
        coursename = c
        print("* create course %s in category %s (%d)" % (c, prefix_courses_jg + getclassgroup(c), categoryid))
        course_create_from_preset(course_get_id(unterstufe_preset), coursename, coursename, categoryid,
                                  get_course_id_name(coursename))

with open('teachers.csv') as teachersfile:
    courses = list(set([s[2] for s in (list(csv.reader(teachersfile, delimiter=';')))]))
    courses_12 = sorted(set([c[0:2].upper() for c in courses if re.match('[A-z][A-z][1-9][1-9][1-9]', c) is not None]))
    courses_11 = sorted(set([c[1:3].upper() for c in courses if re.match('[1-9][a-z][a-z][1-9]', c) is not None]))
    print(courses_11)
    for c in courses_11:
        category_create(c, category_get_id(prefix_courses_jg + '11'), '11_' + c)

    print(courses_12)
    for c in courses_12:
        category_create(c, category_get_id(prefix_courses_jg + '12'), '12_' + c)

    for course in courses:
        if re.match('[1-9][a-z][a-z][1-9]', course) is not None:
            print('11_' + next(x for x in courses_11 if x in course.upper()))
            categoryid = category_get_id_by_idnumber('11_' + next(x for x in courses_11 if x in course.upper()))
        elif re.match('[A-z][A-z][1-9][1-9][1-9]', course) is not None:
            print('12_' + next(x for x in courses_12 if x in course.upper()))
            categoryid = category_get_id_by_idnumber('12_' + next(x for x in courses_12 if x in course.upper()))
        else:
            continue
        coursename = course
        course_create(coursename, categoryid)

for i in range(0, len(ldapusers), 20):
    # next we create users (directly from ldap-users)
    print("* create moodle users from ldapusers")
    result = users_create(ldapusers[i:i + 20])
    if len(ldapusers) - i >= 20:
        max = i + 20
    else:
        max = len(ldapusers)
    for u in range(i, max):
        tmp = next(x for x in result if x['username'] == ldapusers[u].uid)
        ldapusers[u].moodleId = tmp['id']


def isObersufe(s):
    if re.match('[1-9][a-z][a-z][1-9]', s) is not None:
        return True
    elif re.match('[A-z][A-z][1-9][1-9][1-9]', s) is not None:
        return True
    else:
        return False


with open('teachers.csv') as teachersfile:
    tf = sorted(list(csv.reader(teachersfile, delimiter=';')))
    courses = [s for s in tf if isObersufe(s[2])]
    teachers = [t for t in ldapusers if t.cl == 'teachers']
    for i in range(0, len(teachers), 20):
        mteachers = []
        for teacher in teachers[i: i + 20]:
            teacher.classTrainer = []
            for course in tf:
                if course[0] and not isObersufe(course[2]) and re.match('^[a-z]|[A-Z0-9][a-z]*', teacher.givenName).group(0) in course[1] and teacher.sn in course[1]:
                    teacher.classTrainer.append(course[0])
                elif isObersufe(course[2]) and re.match('^[a-z]|[A-Z0-9][a-z]*',teacher.givenName).group(0) in course[1] and teacher.sn in course[1]:
                    teacher.classTrainer.append(course[2])
            teacher.classTrainer = list(set(teacher.classTrainer))
            mteachers.append(teacher)
        enrol_trainers(mteachers)

for i in range(0, len(ldapusers), 20):
    # (manually) enrol users to courses
    # check rolename variables!

    print("* enrol users to their courses")
    enrol_users(ldapusers[i:i + 20])

print('========== DONE ==========')
