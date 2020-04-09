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

import re
import csv
import datetime

import moodle
import ldaphelper

# TODO use yargs for arguments

role_teacher = 'editingteacher'  # the script needs to know the role_id for teacher
role_student = 'student'  # and student for enroling users to courses

cat_students = 'Schüler'  # names for the basic categories in moodle
cat_teachers = 'Lehrer'

rid_students = 5  # to enrol users to a course, the global role id is
rid_teachers = 3  # needed - there seems to be no rest-ish way to get it

teachersroom = 'Lehrerzimmer'  # well... its quite clear, isn't it?

oberstufe = ['11', '12']

unterstufe_preset = "unterstufe_preset"

# machine accounts, adminsitrators, ... will be filtered by gecos data field
gecos_exclude = ['admin 01', 'Programm Administrator', 'Web Administrator', 'Administrator', 'administrator',
                 'LINBO Administrator', 'ExamAccount']

# the key, base-url and endpoint for the moodle REST api
KEY = 'REPLACE_ME'
URL = 'REPLACE_ME'
ENDPOINT = '/webservice/rest/server.php'

ldap_server = 'REPLACE_ME'
ldap_binddn = ''  # not used so far
ldap_bindpw = ''  # anonymous bind
ldap_basedn = 'REPLACE_ME'

prefix_courses_jg = 'Jahrgang '


# -----------------------------------------------------------------


def getclassgroup(name):
    g = re.match('.*?([0-9]+)', name)
    if g is None:
        if name == 'teachers':
            return cat_teachers
        else:
            return cat_students
    else:
        return g.group(0)


def users_create(moodle, userlist):
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
    return moodle.users_create(users)


def enrol_users(moodle, users):
    """ manually enrols users to a course """
    musers = []
    for u in users:
        muser = {}
        if u.cl == 'teachers':
            muser['roleid'] = rid_teachers
        else:
            muser['roleid'] = rid_students

        muser['userid'] = u.moodleId
        muser['courseid'] = m.course_get_id(u.cl)
        if muser['courseid'] is None:
            continue
        musers.append(muser)

    if len(musers) > 0:
        moodle.enrol_users(musers)


def enrol_trainers(moodle, trainers):
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
            mtrainer['courseid'] = m.course_get_id(course)
            if mtrainer['courseid'] is None:
                continue
            mtrainers.append(mtrainer)
    print(mtrainers)

    if len(mtrainers) > 0:
        moodle.enrol_users(mtrainers)


def get_category_id_name(cl):
    if getclassgroup(cl) == cat_students or getclassgroup(cl) == cat_teachers:
        return cl
    jg = int(getclassgroup(cl))
    jg = jg - 5
    year = datetime.datetime.now().year

    if datetime.datetime.now().month < 8:
        year = year - 1

    year = year - jg
    return 'jg' + str(year)


def get_course_id_name(cl):
    if getclassgroup(cl) == cat_students or getclassgroup(cl) == cat_teachers:
        return cl
    letter = re.match('.*?([A-z]+)', cl).group(1)
    return get_category_id_name(cl) + '_' + letter


def convertInt(s):
    try:
        match = next((x for x in oberstufe if x in str(s)), False)
        if match:
            s = match
        int(s)
        return int(s)
    except ValueError:
        return s


def isObersufe(s):
    if re.match('[1-9][a-z][a-z][1-9]', s) is not None:
        return True
    elif re.match('[A-z][A-z][1-9][1-9][1-9]', s) is not None:
        return True
    else:
        return False


# entry point
if __name__ == '__main__':
    ldapusers = ldaphelper.getLdapUsers(ldap_server, ldap_basedn, gecos_exclude)  # get all users

    m = moodle.Moodle(URL + ENDPOINT, KEY)

    # create two main categories in moodle ('Schüler' and 'Lehrer')

    for cn in [cat_teachers, cat_students]:
        print("* create basic category %s" % cn)
        m.category_create(cn, 0)

    # create the classgroup-categories

    # convert classes to int if possible
    sorted_classes = list(set([convertInt((getclassgroup(u.cl))) for u in ldapusers if getclassgroup(u.cl)]))
    # filter upper categories, remove cat_students, cat_teachers and root
    sorted_classes = sorted([s for s in sorted_classes if s != cat_students and s != cat_teachers and s!= "root"])
    print("create classes as subcategory: ", sorted_classes)

    for cg in [str(s) for s in sorted_classes]:
        categoryid = m.category_get_id(cat_students)
        print("* create subcategory", cg, 'in parent', categoryid)
        m.category_create(prefix_courses_jg + cg, categoryid, get_category_id_name(cg))

    # create the courses in the classgroup-categories (and a teachers course in teachers category)
    # every course that is not in category teachers OR any know subcategory will be in students subcat.
    single = sorted(set([u.cl for u in ldapusers if u.cl != 'False' and u.cl != 'jg-11' and u.cl != 'jg-12']))
    for c in single:
        if c == "teachers":
            categoryid = m.category_get_id(cat_teachers)
            coursename = teachersroom
            print("* create course %s in category %s (%d)" % (c, prefix_courses_jg + getclassgroup(c), categoryid))
            m.course_create(coursename, categoryid)
        else:
            categoryid = m.category_get_id(prefix_courses_jg + getclassgroup(c))
            if categoryid is None:
                categoryid = m.category_get_id(cat_students)
            coursename = c
            print("* create course %s in category %s (%d)" % (c, prefix_courses_jg + getclassgroup(c), categoryid))
            m.course_create_from_preset(m.course_get_id(unterstufe_preset), coursename, coursename, categoryid,
                                        get_course_id_name(coursename))
    # create upper courses
    with open('teachers.csv') as teachersfile:
        courses = list(set([s[2] for s in (list(csv.reader(teachersfile, delimiter=';')))]))
        courses_12 = sorted(set([c[0:2].upper() for c in courses if re.match('[A-z][A-z][1-9][1-9][1-9]', c) is not None]))
        courses_11 = sorted(set([c[1:3].upper() for c in courses if re.match('[1-9][a-z][a-z][1-9]', c) is not None]))

        for num, cs in enumerate([courses_11, courses_12]):
            for c in cs:
                    idnumber = str(num + 11) + '_' + c
                    category = prefix_courses_jg + str(num + 11)
                    print("* create category %s with id number %s in %s" % (c, idnumber, category))
                    m.category_create(c, m.category_get_id(category), idnumber)

        for course in courses:
            if re.match('[1-9][a-z][a-z][1-9]', course) is not None:
                print('11_' + next(x for x in courses_11 if x in course.upper()))
                categoryid = m.category_get_id_by_idnumber('11_' + next(x for x in courses_11 if x in course.upper()))
            elif re.match('[A-z][A-z][1-9][1-9][1-9]', course) is not None:
                print('12_' + next(x for x in courses_12 if x in course.upper()))
                categoryid = m.category_get_id_by_idnumber('12_' + next(x for x in courses_12 if x in course.upper()))
            else:
                continue
            coursename = course
            m.course_create(coursename, categoryid)

    # next we create users (directly from ldap-users)
    for i in range(0, len(ldapusers), 20):
        print("* create moodle users from ldapusers")
        result = users_create(m, ldapusers[i:i + 20])
        if len(ldapusers) - i >= 20:
            max = i + 20
        else:
            max = len(ldapusers)
        for u in range(i, max):
            tmp = next(x for x in result if x['username'] == ldapusers[u].uid)
            ldapusers[u].moodleId = tmp['id']

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
            enrol_trainers(m, mteachers)

    for i in range(0, len(ldapusers), 20):
        # (manually) enrol users to courses
        # check rolename variables!

        print("* enrol users to their courses")
        enrol_users(m, ldapusers[i:i + 20])

    print('========== DONE ==========')
