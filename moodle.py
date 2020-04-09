import requests


class Moodle:
    def __init__(self, url, key):
        self.url = url
        self.key = key

    def rest_api_parameters(self, in_args, prefix='', out_dict=None):
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
                self.rest_api_parameters(item, prefix.format(idx), out_dict)
        elif type(in_args) == dict:
            for key, item in in_args.items():
                self.rest_api_parameters(item, prefix.format(key), out_dict)
        return out_dict

    def call(self, fname, **kwargs):
        """Calls moodle API function with function name fname and keyword arguments. """
        parameters = self.rest_api_parameters(kwargs)
        parameters.update({"wstoken": self.key, 'moodlewsrestformat': 'json', "wsfunction": fname})

        import json
        f = open('params.txt', 'w')
        f.write(json.dumps(parameters))
        f.close()

        response = requests.post(self.url, data=parameters).json()
        if type(response) == dict and response.get('exception'):
            raise SystemError("Error calling Moodle API\n", response)
        return response

    def category_create(self, name, parentid, idnumber=None):
        if idnumber is None:
            idnumber = name.lower()
        """ Create Categories with 'name' and 'parentid' """
        return self.call('core_course_create_categories',
                         categories=[{'name': name, 'parent': parentid, 'idnumber': idnumber}])

    def category_get_id(self, name):
        """ get the id of a given category """

        res = self.call('core_course_get_categories', criteria=[{'key': 'name', 'value': name.lower()}])
        if res != []:
            res = [x for x in res if x['name'] == name]
            return res[0]['id']
        else:
            return None

    def category_get_id_by_idnumber(self, idnumber):
        """ get the id of a given category """

        res = self.call('core_course_get_categories', criteria=[{'key': 'idnumber', 'value': idnumber}])
        if res != []:
            res = [x for x in res if x['idnumber'] == idnumber]
            return res[0]['id']
        else:
            return None

    def course_create(self, name, categoryid, displayname=None):
        """ create a course with name and category-id """
        if displayname is None:
            course = {'fullname': name, 'shortname': name, 'categoryid': categoryid}
        else:
            course = {'fullname': name, 'shortname': name, 'categoryid': categoryid, 'name': displayname}
        return self.call('core_course_create_courses', courses=[course])

    def course_create_from_preset(self, preset_course_id, fullname, shortname, category_id, idnumber=None):
        id = \
        self.call('core_course_duplicate_course', courseid=preset_course_id, fullname=fullname, shortname=shortname,
                  categoryid=category_id)['id']

        if idnumber is not None:
            self.call('core_course_update_courses',
                      courses=[{'id': id, 'idnumber': idnumber, 'categoryid': category_id}])

    def course_get_id(self, name):
        """ returns course id or None"""
        crs_list = self.call('core_course_get_courses_by_field', field='shortname', value=name)['courses']
        if len(crs_list) == 0:
            print(f'No course found with shortname {name}!')
        elif len(crs_list) == 1:
            return crs_list[0]['id']
        else:
            print(f'Shortname {name} not unique. There are {len(crs_list)} courses with this shortname.')
        return None

    def users_create(self, userlist):
        """ Create moodle-user from a list of ldap-users """
        return self.call('core_user_create_users', users=userlist)

    def enrol_users(self, users):
        if len(users) > 0:
            self.call('enrol_manual_enrol_users', enrolments=users)

    def users_get(self, criteria):
        return self.call('core_user_get_users', criteria=[criteria])
