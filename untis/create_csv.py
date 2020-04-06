import csv
import codecs

ENCODING = 'ISO-8859-14'

def findName(short, longs):
    for long in longs:
        if (short == long[0]):
            longname = long[1].replace(' ', '').replace('-', '')
            longname = longname.split(';')
            if len(longname) <= 1:
                longname = longname[0]
            else:
                longname = longname[1] + ' ' + longname[0]
            return longname.replace("ä","ae").replace("Ä","Ae").replace("ö","oe").replace("Ö","oe").replace("ü","ue").replace("Ü","ue")
    return ''

with codecs.open('GPU004.TXT', 'r', ENCODING) as csvfile:
    with codecs.open('GPU001.TXT', 'r', ENCODING) as coursefile:
        with open('teachers.csv', 'w') as final:
            courses = list(csv.reader(coursefile, delimiter=';'))
            names = list(csv.reader(csvfile, delimiter=';'))
            li = []
            for course in courses:
                longname = findName(course[2], names)
                #print(course[1] + ';' + longname + ';' + course[3] + '\r\n')
                li.append(course[1] + ';' + longname + ';' + course[3])
            li = list(set(li))
            for l in li:
                final.write(l + '\r\n')
