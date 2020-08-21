#!/usr/bin/python3
from icalendar import Calendar, Event
import datetime
import pytz
import dateutil.parser
import argparse
import re

ICALORG = "/Users/piercewang/Dropbox/org/gcal.org"
ICSDIR = "/Users/piercewang/Documents/Projects/Programming/emacs/icalsync/ohs_assignments.ics"
tz = pytz.timezone('America/Los_Angeles') # Assuming PST time zone

def get_url(component):
    """Documentation for get_url

    Args: component
    :param component: A component from gcal.walk()
    
    :returns: A string with a URL to the assignment on canvas
    :raises keyError: None
    """
    fullurl = str(component.get('url'))
    course_id = re.search(r'course_([0-9]*)', fullurl)
    course_id = course_id.group(1) if course_id != None else None
    assignment = re.search(r'assignment_([0-9]*)', fullurl)
    assignment = True if assignment != None else False
    if assignment == False:
        return((fullurl, course_id, assignment))
    else:
        return((f'https://spcs.instructure.com/courses/{course_id}/assignments/{assignment}', course_id, assignment))

def get_data(ICSDIR):
    """Documentation for get_data()

    Args: ICSDIR
    :param ICSDIR: A directory path to the ics file.
    
    :returns: A dictionary of courses which each have lists of assignment dictionaries.
              Structure is as so: {course: [{headline, deadline, url}, {headline, deadline, url}]}
    :raises keyError: None
    """
    course_assignments = {}
    with open(ICSDIR,'rb') as g:
        gcal = Calendar.from_ical(g.read())
        for component in gcal.walk():
            if component.name == "VEVENT":
                url, course_id, assignment = get_url(component)
                if course_id != None:
                    headline = str(component.get('summary'))
                    course = re.search(r"\[(.*)\]$", headline)
                    course_code = re.search(r"\[([A-Z0-9]{4,7}).*\]", headline) # Obtained course code
                    if course_code != None:
                        course_code = course_code.group(1)
                    else:
                        course_code = course.group(1)

                    # Cutting down headline
                    headline = re.search(r"^ ?(.*) \[.*\]", headline).group(1)
                    extra_bit = re.search(r"(.*) \(.{30,65}\)", headline)
                    # Deal with extra bit (e.g. "(American Culture & Society~ - Smith - 3(B))")
                    if extra_bit != None:
                        headline = extra_bit.group(1)

                    if course_code not in course_assignments: # Adding course for the first time
                        course_assignments[course_code] = []
                    course_assignments[course_code].append({"task": assignment, "headline": headline, "timestamp": component.get('dtend').dt, "url": url, "todo": "TODO " if assignment else ""})
    return course_assignments

def change_times(course_assignments):
    """Documentation for change_times

    Fix when some times are set to the wrong time due to being set as full day tasks in the calendar (when due at 23:59)
    Args: course_assignments
    :param course_assignments: The dictionary with the hierarchy of assignments.
    
    :returns: A dict of course_assignments with all times fixed
    :raises keyError: None
    """
    for course, assignments in course_assignments.items():
        for assignment in assignments:
            if assignment["timestamp"].hour == 0 and assignment["timestamp"].minute == 0 and assignment["timestamp"].tzinfo == None: # Then scheduled as full day task
                assignment["timestamp"] = assignment["timestamp"].replace(hour=23, minute=59, tzinfo=tz)
            else: # Specific time
                assignment["timestamp"] = assignment["timestamp"].astimezone(tz)
    return course_assignments

def filter_assignments(course_assignments, final_delta = 14):
    """Documentation for filter_assignments

    Args: course_assignments, final_delta
    :param course_assignments: The dict of course_assignments
    :param final_delta: The number of days to look into the future. Default is 14 days in advance
    
    :returns: A dict of only the assignments that fall within the dates given
    :raises keyError: None
    """
    start_date = datetime.datetime.now(tz)
    end_date = start_date + datetime.timedelta(days=final_delta)
    filtered_assignments = {}
    for course, assignments in course_assignments.items():
        for assignment in assignments:
            if (end_date >= assignment["timestamp"] >= start_date): # Assignment is in date rage
                if course not in filtered_assignments:
                    filtered_assignments[course] = []
                filtered_assignments[course].append(assignment)
    return filtered_assignments

    
def create_org(orgdir, assignments):
    """Documentation for create_org

    Args: orgdir, assignments
    :param orgdir: path to org file
    :param assignments: dict of assignments
    
    :returns: Nothing, writes to given org file
    :raises keyError: None
    """
    daysoftheweek = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    with open(orgdir,'w') as orgfile:
        orgfile.write("#+PRIORITIES: A E B\n#+FILETAGS: :OHS:gcal:\n#+STARTUP: content indent")
        for course, assignments in course_assignments.items():
            if assignments != []:
                orgfile.write(f'\n* {course}')
                if course.find(" ") == -1:
                    orgfile.write(f' :{course}:')
                for assignment in assignments:
                    orgfile.write(f'\n** {assignment["todo"]}{assignment["headline"]}')
                    if assignment["task"] == False:
                        orgfile.write(f'\n<{assignment["timestamp"].year:02d}-{assignment["timestamp"].month:02d}-{assignment["timestamp"].day:02d} {daysoftheweek[assignment["timestamp"].weekday()]}>')
                    else:
                        orgfile.write(f'\nDEADLINE: <{assignment["timestamp"].year:02d}-{assignment["timestamp"].month:02d}-{assignment["timestamp"].day:02d} {daysoftheweek[assignment["timestamp"].weekday()]} {assignment["timestamp"].hour:02d}:{assignment["timestamp"].minute:02d}>')
                    if assignment["url"] != None:
                        orgfile.write(f'\n:PROPERTIES:\n:LINK:     {assignment["url"]}\n:END:')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse assignments from ics file orgmode assignments.')
    parser.add_argument('ICS', help="Path to downloaded ICS File",
                        type=str)
    parser.add_argument('ORG', help="Path to intended orgmode File",
                        type=str)
    parser.add_argument('-td', '--timedelta', nargs='?', help="Time Delta (How far to look into the future. Default: 14 days",
                        type=int)
    parser.add_argument('-ig', '--ignore', nargs='*', help="Class(es) to ignore",
                        type=str)
    args = parser.parse_args()
    ICALORG = args.ORG
    ICSDIR = args.ICS
    course_assignments = get_data(ICSDIR)
    course_assignments = change_times(course_assignments)
    if args.timedelta:
        course_assignments = filter_assignments(course_assignments, final_delta = args.timedelta)
    else:
        course_assignments = filter_assignments(course_assignments)
    if args.ignore:
        for class_code in args.ignore:
            if class_code in course_assignments:
                course_assignments.pop(class_code)
    create_org(ICALORG, course_assignments)
