#!/Users/piercewang/anaconda3/bin/python
from icalendar import Calendar, Event
import datetime
import pytz
import dateutil.parser
import argparse

ICALORG = "/Users/piercewang/Dropbox/org/gcal.org"
ICSDIR = "/Users/piercewang/Documents/Projects/Programming/emacs/icalsync/2018-19_assignments.ics"
tz = pytz.timezone('America/Los_Angeles') # Assuming PST time zone
identifiers = {'OE020B': ['[OE020B - Critical Theory Historical Imagination~ - S1]'],
               'ODFRL': ['[ODFRL - Core: Democracy, Freedom, Rule of Law* - S1]'],
               'UM52A': ['[UM52A - UN Multivar Differential Calc* - S1]'],
               'OH011A': ['(American Culture & Society~ - Smith - 3(B))',
                          '[OH011A - American Culture & Society~ - S1]'],
               'OP005': ['[OP005 - Honors Physics - S1]'],
               }

def getURL(component): # Get URL using component from gcal.walk()
    fullurl = str(component.get('url'))
    courseindex = fullurl.find('course_')+7
    course = fullurl[courseindex:courseindex+4]
    assignmentindex = fullurl.find('assignment_')+11
    assignment = fullurl[assignmentindex:assignmentindex+5]
    return(f'https://spcs.instructure.com/courses/{course}/assignments/{assignment}')

def get_data(ICSDIR):
    assignmentlist = {}
    breakloop = False
    with open(ICSDIR,'rb') as g:
        gcal = Calendar.from_ical(g.read())
        for component in gcal.walk():
            if component.name == "VEVENT":
                headline = str(component.get('summary'))
                for course, strings in identifiers.items(): #find what course the headline belongs to
                    for identifier in strings:
                        findidentifier = headline.find(identifier)
                        if findidentifier != -1:
                            event_course = course
                            headline = headline[0:findidentifier-1]
                            breakloop = True
                            break
                    if breakloop == True:
                        breakloop = False
                        url = getURL(component)
                        # print(f'{headline}: {component.get("dtend").dt}')
                        assignmentlist[headline] = [component.get('dtend').dt, event_course, url]
                        break
    return(assignmentlist)

def change_times(assignmentlist):
    """
    Fix when some times are set to the wrong time due to being set as full day tasks in the calendar
    """
    assignments = assignmentlist
    for assignment, attributes in assignments.items():
        if attributes[0].hour == 0 and attributes[0].minute == 0 and attributes[0].tzinfo == None: # Then scheduled as full day task
            attributes[0] = attributes[0].replace(hour=23, minute=59, tzinfo=tz)
        else: # Specific time
            attributes[0] = attributes[0].astimezone(tz)
    return assignments

def filter_assignments(assignmentlist, final_delta = 14):
    """
    Filter assignments by time, default 14 days in advance
    """
    start_date = datetime.datetime.now(tz)
    end_date = start_date + datetime.timedelta(days=final_delta)
    final_assignments = {}
    for assignment, data in assignmentlist.items():
        if (end_date >= data[0] >= start_date):
            final_assignments[assignment] = data
    return final_assignments

    
def create_org(orgdir, assignments):
    daysoftheweek = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    with open(orgdir,'w') as orgfile:
        orgfile.write("#+PRIORITIES: A E B\n#+FILETAGS: :OHS:gcal:\n#+STARTUP: content")
        for course, attributes in identifiers.items():
            orgfile.write(f'\n* {course} :{course}:')
            for assignment, data in assignments.items():
                if data[1] == course:
                    orgfile.write(f'\n** TODO {assignment}\n   DEADLINE: <{data[0].year:02d}-{data[0].month:02d}-{data[0].day:02d} {daysoftheweek[data[0].weekday()]} {data[0].hour:02d}:{data[0].minute:02d}>\n   :PROPERTIES:\n   :LINK:     {data[2]}\n   :END:')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse assignments from ics file orgmode assignments.')
    parser.add_argument('ICS', help="Path to downloaded ICS File",
                        type=str)
    parser.add_argument('ORG', help="Path to intended orgmode File",
                        type=str)
    parser.add_argument('-td', '--timedelta', nargs='?', help="Time Delta (How far to look into the future. Default: 14 days",
                        type=int)
    args = parser.parse_args()
    ICALORG = args.ORG
    ICSDIR = args.ICS
    assignmentlist = get_data(ICSDIR)
    assignments_changed = change_times(assignmentlist)
    if args.timedelta:
        create_org(ICALORG, filter_assignments(assignments_changed, final_delta = args.timedelta))
    else:
        create_org(ICALORG, filter_assignments(assignments_changed))
