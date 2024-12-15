#!/usr/bin/python3
from icalendar import Calendar, Event
import datetime
import pytz
import dateutil.parser
import argparse
import re

tz = pytz.timezone('America/New_York') # Assuming PST time zone

def get_component_info(component, base_url):
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
        calendar_event = re.search(r'calendar_event_([0-9]*)', fullurl)
        calendar_event = calendar_event.group(1) if calendar_event != None else None
        return((f'https://{base_url}/courses/{course_id}/calendar_events/{calendar_event}', course_id, False))
    else:
        return((f'https://{base_url}/courses/{course_id}/assignments/{assignment}', course_id, True))

def search_course(event_summary):
    """Documentation for search_course

    Args: headline
    :param event_summary: A string representing the component summary
    (given ics headline)
    
    :returns: A string, course_title, which is the full course name. :raises
    keyError: None

    """
    course = re.search(r"\[(.*)\]$", event_summary)
    # course_code = re.search(r"\[([A-Z]{1,2}[0-9]{3,5}).*\]", event_summary) # Attempting to find course code
    # if course_code != None: # If title doesn't have course code, use course title
    #     course_code = course_code.group(1)
    # else:
    #     course_code = course.group(1)
    return course.group(1)

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

def make_date(ics_event, assignment):
    """Documentation for make_date

    Args: ics_event, assignment
    :param ics_event: ics event obtained by walking the ics file
    :param assignment: boolean representing whether the component is an assignment or not

    :returns: a tuple if not an assignment with start and end dates or one
                singular datetime if it is an assignment which is the due date
    :raises keyError: None

    """
    if assignment:
        due_date = ics_event.get('dtend').dt if ics_event.get('dtend') != None else ics_event.get('dtstart').dt
        if type(due_date) == datetime.date:
            return (datetime.datetime(due_date.year, due_date.month, due_date.day, 23, 59, tzinfo=tz), None)
        elif due_date.tzinfo == None:
            return (due_date.replace(hour=23, minute=59, tzinfo=tz), None)
        else:
            return (due_date.astimezone(tz), None)
    else:
        dtstart = ics_event.get('dtstart').dt
        dtend = ics_event.get('dtend').dt if ics_event.get('dtend') is not None else ics_event.get('dtstart').dt
        # print(type(dtstart))
        if type(dtstart) == datetime.date:
            date_start = datetime.datetime(dtstart.year, dtstart.month, dtstart.day, 00, 00, tzinfo=tz)
        else:
            date_start = dtstart.astimezone(tz) if dtstart.tzinfo != None else dtstart.replace(hour=0, minute=0, tzinfo=tz)
        if type(dtend) == datetime.date:
            date_end = datetime.datetime(dtend.year, dtend.month, dtend.day, 23, 59, tzinfo=tz)
        else:
            date_end = dtend.astimezone(tz) if dtend.tzinfo != None else dtend.replace(hour=0, minute=0, tzinfo=tz)
        return (date_start, date_end)


def insert_task(course_information, course_title, course_id, headline, due, url, description):
    if course_title not in course_information:
        course_information[course_title] = []
    course_information[course_title].append({"id": course_id, "headline": headline, "due": due, "url": url, "description": description})

def insert_event(course_information, course_title, course_id, headline, start_dt, end_dt, url, description):
    if course_title not in course_information:
        course_information[course_title] = []
    course_information[course_title].append({"id": course_id, "headline": headline, "start_dt": start_dt, "end_dt": end_dt, "url": url, "description": description})

def in_file(orgignorefile, url):
    """Documentation for in_file

    Args: orgignorefile, url
    :param orgignorefile: Path to the org file to search
    :param url: A string with a url
    
    :returns: True if the url is found in orgignorefile and False if it's not
    :raises keyError: None
    """
    with open(orgignorefile) as f:
        if url in f.read():
            return True
        else:
            return False

def process_component(course_information, component, base_url, orgignorefile, ignore, date_delta):
    if component.name != "VEVENT":
        return None

    url, course_id, assignment = get_component_info(component, base_url)

    if course_id == None or in_file(orgignorefile, url):
        return None

    component_summary = component.get('summary')
    event_description = component.get('description')
    course_title = search_course(component_summary)
    headline = filter_headline(component_summary)

    if course_title in ignore:
        return None

    date_start, date_end = make_date(component, assignment)
    date_filter_start = datetime.datetime.now(tz) - datetime.timedelta(days=14)
    date_filter_end = datetime.datetime.now(tz) + datetime.timedelta(days=date_delta)

    if (date_filter_start <= date_start <= date_filter_end):
        if assignment:
            insert_task(course_information, course_title, course_id, headline, date_start, url, event_description)
        else:
            insert_event(course_information, course_title, course_id, headline, date_start, date_end, url, event_description)

def get_data(icsfile, base_url, orgignorefile, ignore, date_delta):
    """Documentation for get_data()

    Args: ICSDIR :param icsfile: A directory path to the ics file.
    :param ignore: An optional arg which is a list of course codes to
    ignore :param date_delta: An optional arg which is an integer of
    how many days in the future to look
    
    :returns: A dictionary of courses which each have lists of
    component dictionaries. The component dictionary is identified as
    a task if it has a "due" entry and as an event if it has
    "start_dt" and "end_dt" entries.
              Structure is as so: {course_code: [{headline, due, url},
              {headline, start_dt, end_dt, url}]}
    :raises keyError: None
    """
    course_information = {}
    with open(icsfile,'rb') as g:
        gcal = Calendar.from_ical(g.read())
        for component in gcal.walk():
            process_component(course_information, component, base_url, orgignorefile, ignore, date_delta)
    return course_information

def org_course_creation(course, assignments):
    daysofweek = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    output = ""

    if assignments == []:
        return output

    output += f'\n* {course}'
    output += f' :{assignments[0]["id"]}:'

    for comp in assignments:
        if "due" in comp:
            output += f'\n** NEXT {comp["headline"]}'
            output += f'\nDEADLINE: <{comp["due"].year:02d}-{comp["due"].month:02d}-{comp["due"].day:02d} {daysofweek[comp["due"].weekday()]} {comp["due"].hour:02d}:{comp["due"].minute:02d}>'
        else:
            output += f'\n** {comp["headline"]}'
            if comp["start_dt"] == comp["end_dt"]:
                output += f'\n<{comp["start_dt"].year:02d}-{comp["start_dt"].month:02d}-{comp["start_dt"].day:02d} {daysofweek[comp["start_dt"].weekday()]}>'
            else:
                output += f'\n<{comp["start_dt"].year:02d}-{comp["start_dt"].month:02d}-{comp["start_dt"].day:02d} {daysofweek[comp["start_dt"].weekday()]} {comp["start_dt"].hour:02d}:{comp["start_dt"].minute:02d}-{comp["end_dt"].hour:02d}:{comp["end_dt"].minute:02d}>'
        output += f'\n:PROPERTIES:\n:LINK:     {comp["url"]}\n:END:'
        if comp["description"] is not None:
            output += "\n " + comp["description"].replace("\n", "\n ")
        output += "\n"

    return output

def create_org(orgdir, course_information, fileprefix):
    """Documentation for create_org

    Args: orgdir, assignments
    :param orgdir: path to org file
    :param assignments: dict of assignments
    
    :returns: Nothing, writes to given org file
    :raises keyError: None
    """
    with open(orgdir,'w') as orgfile:
        orgfile.write(fileprefix)
        for course, assignments in course_information.items():
            orgfile.write(org_course_creation(course, assignments))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse assignments from ics file orgmode assignments.')
    parser.add_argument('ICS', help="Path to downloaded ICS File",
                        type=str)
    parser.add_argument('ORG', help="Path to intended orgmode File",
                        type=str)
    parser.add_argument('URL', help="Base URL to canvas",
                        type=str)
    parser.add_argument('-fp', '--fileprefix', nargs='?', default="", help="Text to put at beginnign of file (e.g. for org-roam id)",
                        type=str)
    parser.add_argument('-oi', '--orgignorefile', nargs='?', default="", help="Path to an orgmode file to know which assignments are already in progress.",
                        type=str)
    parser.add_argument('-td', '--timedelta', nargs='?', default=14, help="Time Delta (How far to look into the future. Default: 14 days",
                        type=int)
    parser.add_argument('-ig', '--ignore', nargs='*', default=[], help="Class(es) to ignore",
                        type=str)
    args = parser.parse_args()
    icsfile = args.ICS
    icalorg = args.ORG
    base_url = args.URL
    course_information = get_data(icsfile, base_url, args.orgignorefile, args.ignore, args.timedelta)
    create_org(icalorg, course_information, args.fileprefix)
