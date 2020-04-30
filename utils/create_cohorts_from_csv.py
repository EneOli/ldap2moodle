import codecs
import csv
import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

import ldaphelper
import moodle

ENCODING = 'ISO-8859-14'

category_11_idnumber = "REPLACE_ME"
category_12_idnumber = "REPLACE_ME"

ldap_server = 'REPLACE_ME'
ldap_binddn = ''  # not used so far
ldap_bindpw = ''  # anonymous bind
ldap_basedn = 'REPLACE_ME'

KEY = 'REPLACE_ME'
URL = 'REPLACE_ME'
ENDPOINT = '/webservice/rest/server.php'

''''--------------------------------------------------------------------------------'''
ldapusers = ldaphelper.getLdapUsers(ldap_server, ldap_basedn, [])  # get all users

m = moodle.Moodle(URL + ENDPOINT, KEY)

category_11 = m.category_get_id_by_idnumber(category_11_idnumber)
category_12 = m.category_get_id_by_idnumber(category_12_idnumber)


def findShort(first, second, ldapusers):
    first = first.replace("ä", "ae").replace("Ä", "Ae").replace("ö", "oe").replace("Ö", "oe").replace("ü", "ue").replace("Ü", "ue").replace('ß', 'ss').replace(' ', '').replace('-', '').replace('von', '')
    second = second.replace("ä", "ae").replace("Ä", "Ae").replace("ö", "oe").replace("Ö", "oe").replace("ü", "ue").replace("Ü", "ue").replace('ß', 'ss').replace(' ', '').replace('-','').replace('von', '')
    for user in ldapusers:
        if user.givenName == first and user.sn == second:
            return user.uid
    return None


with codecs.open('export_aus_schulverwaltung.csv', 'r', ENCODING) as csvfile:
    courses = list(csv.reader(csvfile, delimiter=';'))
    teacherlist = []
    courses.pop(0)
    cs = []
    ccx = []
    with open('5_Globale_Gruppen_in_Kurse_Plugin.csv', "w") as plugin:
        with open('4_Nutzer_in_globale_Gruppen.csv', "w") as cohorts:
            cohorts.write('username,cohort1\r\n')
            with open('3_Globale_Gruppen_anlegen.csv', "w") as cc:
                cc.write('name,idnumber,description, category\r\n')
                with open('2_Lehrer_einschreiben.csv', "w") as teachers:
                    teachers.write('username,course1,role1\r\n')
                    with open("1_Kurse_anlegen.csv", "w") as outfile:
                        outfile.write("shortname,fullname,category,summary,enrolment_1,enrolment_1_role,enrolment_1_enrolperiod,role_student\r\n")
                        for course in courses:
                            teacher_short = course[0][-3:].replace(' ', '').replace('-', '')
                            shortname = 'TG ' + teacher_short
                            longname = 'TG ' + course[1]
                            summary = "TG Angelegenheiten"
                            student = findShort(course[4], course[3], ldapusers)
                            if student is None:
                                print(course[4] + ' ' + course[3] + " notfound in ldap")
                                continue

                            teacher_uid = findShort(course[2], course[1], ldapusers)
                            if teacher_uid is not None:
                                teacherlist.append(teacher_uid + "," + shortname + ',' + 'editingteacher\r\n')

                            if course[0][0:2] == "11":
                                category = category_11
                            else:
                                category = category_12

                            cohorts.write(student + ',' + shortname + '\r\n')
                            ccx.append(shortname + ',' + shortname + ',TG Angelegenheiten' + ",1\r\n")

                            print(shortname, ',', longname, ',', category, ',', summary, ',', 'manual', ',', 'student',
                                  ',,\r\n')
                            cs.append(shortname + ',' + longname + ',' + str(
                                category) + ',' + summary + ',' + 'manual' + ',' + 'student' + ',,' + '\r\n')
                            cs = list(set(cs))
                            plugin.write(
                                'add,' + 'cohort,' + shortname + ',' + shortname + ',0,' + shortname + ',student\r\n')
                        outfile.write(''.join(cs))
                        teachers.write(''.join(list(set(teacherlist))))
                        cc.write(''.join(list(set(ccx))))
