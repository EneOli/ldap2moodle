import ldap as pythonLdap


class LdapUser:
    def __init__(self, uid, sn, givenName, mail, cl):
        self.uid = str(uid)
        self.sn = str(sn)
        self.givenName = str(givenName)
        self.mail = str(mail)
        self.cl = str(cl)
        self.moodleId = None
        self.classTrainer = None


def getLdapUsers(ldap_server, ldap_basedn, exclude=[]):
    """ reads the linuxmuster.net users from the server ldap """
    ldap = pythonLdap.initialize(ldap_server)  # initialize the ldap object
    basedn = ldap_basedn
    searchFilter = "(objectclass=person)"
    searchAttribute = []
    searchScope = pythonLdap.SCOPE_SUBTREE  # scope entire subtree
    # ldap connect
    try:
        pythonLdap.set_option(pythonLdap.OPT_X_TLS_REQUIRE_CERT, pythonLdap.OPT_X_TLS_NEVER)  # ssl cert ignore
        ldap.protocol_version = pythonLdap.VERSION3
        ldap.simple_bind_s()
    except pythonLdap.INVALID_CREDENTIALS:
        print("Username or password is incorrect.")
        raise RuntimeError("Username or password is incorrect.")
    except pythonLdap.LDAPError as e:  # ldap bind failure
        if type(e['message']) == dict and 'desc' in e['message']:
            print(e['message']['desc'])
        else:
            print(e)
        raise e

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
                    if d['gecos'][0].decode() not in exclude:
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
