#!/usr/bin/python3
from icalendar import Calendar, Event
import datetime
import pytz
import dateutil.parser
import argparse
import re

tz = pytz.timezone('America/Los_Angeles') # Assuming PST time zone

def get_component_info(component):
    """Documentation for get_url

    Args: component
    :param component: A component from gcal.walk()
    
    :returns: fullurl: a string with the url of the component,
    course_id: a string with the link id of the component, assignment:
    boolean; True if component is task, False if not
    :raises keyError: None
    """
    fullurl = str(component.get('url'))
    course_id = re.search(r'course_([0-9]*)', fullurl)
    course_id = course_id.group(1) if course_id != None else None
    assignment = re.search(r'assignment_([0-9]*)', fullurl)
    assignment = assignment.group(1) if assignment != None else None
    if not assignment:
        return((fullurl, course_id, False))
    else:
        return((f'https://spcs.instructure.com/courses/{course_id}/assignments/{assignment}', course_id, True))

def search_course(event_summary):
    """Documentation for search_course

    Args: headline
    :param event_summary: A string representing the component summary
    (given ics headline)
    
    :returns: A string, course_code, which is either the course code,
    or if the headline did not contain a course code, is the full
    course name.  :raises keyError: None
    """
    course = re.search(r"\[(.*)\]$", event_summary)
    course_code = re.search(r"\[([A-Z0-9]{4,7}).*\]", event_summary) # Attempting to find course code
    if course_code != None: # If title doesn't have course code, use course title
        course_code = course_code.group(1)
    else:
        course_code = course.group(1)
    return course_code

def filter_headline(event_summary):
    """Documentation for filter_headline

    Args: headline
    :param event_summary: A string representing the component summary
    (given ics headline)

    :returns: a string with the title of an assignment or event
    without any extrenuous information about the course
    :raises keyError: None
    """
    headline = re.search(r"^ ?(.*) \[.*\]", event_summary).group(1)
    extra_bit = re.search(r"(.*) \(.{30,65}\)", event_summary)
    if extra_bit != None: # Deal with extra bit (e.g. "(American Culture & Society~ - Smith - 3(B))")
        headline = extra_bit.group(1)
    return headline

def fix_timezone(date_time, task):
    """Documentation for fix_timezone

    Args: course_assignments
    :param date_time: A datetime instance
    
    :returns: A dict of course_assignments with all times fixed
    :raises keyError: None
    """
    if task == True and date_time.tzinfo == None: # Is a task, set due date as 23:59
        date_time = date_time.replace(hour=23, minute=59, tzinfo=tz)
    elif date_time.tzinfo == None: # Is event, set time to be all day
        date_time = date_time.replace(hour=0, minute=0, tzinfo=tz)
    else:
        date_time = date_time.astimezone(tz)
    return date_time

def insert_task(course_information, course_code, headline, due, url):
    # Fix time zone
    if course_code not in course_information:
        course_information[course_code] = []
    course_information[course_code].append({"headline": headline, "due": due, "url": url})

def insert_event(course_information, course_code, headline, start_dt, end_dt, url):
    # Fix time zones
    if course_code not in course_information:
        course_information[course_code] = []
    course_information[course_code].append({"headline": headline, "start_dt": start_dt, "end_dt": end_dt, "url": url})
    
def get_data(icsfile, ignore, date_delta):
    """Documentation for get_data()

    Args: ICSDIR :param icsfile: A directory path to the ics file.
    :param ignore: An optional arg which is a list of course codes to
    ignore :param date_delta: An optional arg which is an integer of
    how many days in the future to look
    
    :returns: A dictionary of courses which each have lists of
    component dictionaries. The component dictionary is identified as
    a task if it has a "due" entry and as an event if it has
    "start_dt" and "end_dt" entries.
              Structure is as so: {course_code: [{headline, due, url}, {headline, start_dt, end_dt, url}]}
    :raises keyError: None
    """
    course_information = {}
    with open(icsfile,'rb') as g:
        gcal = Calendar.from_ical(g.read())
        for component in gcal.walk():
            if component.name == "VEVENT":
                url, course_id, assignment = get_component_info(component)
                if course_id != None:
                    component_summary = component.get('summary')
                    course_code = search_course(component_summary)
                    headline = filter_headline(component_summary)
                    if course_code not in ignore:
                        start_dt = fix_timezone(component.get('dtstart').dt, assignment)
                        end_dt = fix_timezone(component.get('dtend').dt, assignment)
                        date_filter_start = datetime.datetime.now(tz)
                        date_filter_end = date_filter_start + datetime.timedelta(days=date_delta)
                        if (date_filter_start <= end_dt <= date_filter_end):
                            if assignment == True:
                                insert_task(course_information, course_code, headline, end_dt, url)
                            else:
                                insert_event(course_information, course_code, headline, start_dt, end_dt, url)
    return course_information
    
def create_org(orgdir, course_information):
    """Documentation for create_org

    Args: orgdir, assignments
    :param orgdir: path to org file
    :param assignments: dict of assignments
    
    :returns: Nothing, writes to given org file
    :raises keyError: None
    """
    daysofweek = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    with open(orgdir,'w') as orgfile:
        orgfile.write("#+PRIORITIES: A E B\n#+FILETAGS: :OHS:scal:\n#+STARTUP: content indent")
        for course, components in course_information.items():
            if components != []:
                orgfile.write(f'\n* {course}')
                if course.find(" ") == -1:
                    orgfile.write(f' :{course}:')
                for comp in components:
                    if "due" in comp:
                        orgfile.write(f'\n** NEXT {comp["headline"]}')
                        orgfile.write(f'\nDEADLINE: <{comp["due"].year:02d}-{comp["due"].month:02d}-{comp["due"].day:02d} {daysofweek[comp["due"].weekday()]} {comp["due"].hour:02d}:{comp["due"].minute:02d}>')
                    else:
                        orgfile.write(f'\n** {comp["headline"]}')
                        if comp["start_dt"] == comp["end_dt"]:
                            orgfile.write(f'\n<{comp["start_dt"].year:02d}-{comp["start_dt"].month:02d}-{comp["start_dt"].day:02d} {daysofweek[comp["start_dt"].weekday()]}>')
                        else:
                            orgfile.write(f'\n<{comp["start_dt"].year:02d}-{comp["start_dt"].month:02d}-{comp["start_dt"].day:02d} {daysofweek[comp["start_dt"].weekday()]} {comp["start_dt"].hour:02d}:{comp["start_dt"].minute:02d}-{comp["end_dt"].hour:02d}:{comp["end_dt"].minute:02d}>')
                    orgfile.write(f'\n:PROPERTIES:\n:LINK:     {comp["url"]}\n:END:')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse assignments from ics file orgmode assignments.')
    parser.add_argument('ICS', help="Path to downloaded ICS File",
                        type=str)
    parser.add_argument('ORG', help="Path to intended orgmode File",
                        type=str)
    parser.add_argument('-td', '--timedelta', nargs='?', default=14, help="Time Delta (How far to look into the future. Default: 14 days",
                        type=int)
    parser.add_argument('-ig', '--ignore', nargs='*', default=[], help="Class(es) to ignore",
                        type=str)
    args = parser.parse_args()
    icsfile = args.ICS
    icalorg = args.ORG
    course_information = get_data(icsfile, ignore=args.ignore, date_delta=args.timedelta)
    create_org(icalorg, course_information)
