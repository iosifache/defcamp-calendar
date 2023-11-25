"""Dummy source file."""

import sys
import typing
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event

SCHEDULE_WEBPAGE = "https://def.camp/schedule/"


@dataclass
class ConferenceDetails:
    """Class storing the relevant details of the conference."""

    start_day: int
    start_month: int
    start_year: int


@dataclass
class EventFacade:
    """Class storing the relevant details of an event."""

    parent_conference: ConferenceDetails
    day: str
    track: int
    start_time: str
    stop_time: str
    title: str
    speaker: str
    speaker_position: str

    def generate_ics_event(
        self: "EventFacade",
    ) -> Event:
        """Generate an ICS event with the details from the event facade.

        Args:
            ics_event (Event): ICS event
            facade (EventFacade): Event facade
        """
        ics_event = Event()

        ics_event.name = f"{self.title}"
        if self.speaker is not None and self.speaker_position is not None:
            ics_event.description = (
                f"Speaker: {self.speaker} ({self.speaker_position})"
            )
        ics_event.begin = (
            f"{self.parent_conference.start_year}-"
            f"{self.parent_conference.start_month}-{self.day} "
            f"{self.start_time}:00"
        )
        ics_event.end = (
            f"{self.parent_conference.start_year}-"
            f"{self.parent_conference.start_month}-{self.day} "
            f"{self.stop_time}:00"
        )
        ics_event.location = "Track " + ("I" if self.track == 1 else "II")

        return ics_event


def get_html() -> str:
    """Get the content of the schedule page.

    Returns:
        str: HTML content
    """
    response = requests.get(SCHEDULE_WEBPAGE, timeout=1)

    return response.text


def convert_html_to_events(
    html: str,
    conference: ConferenceDetails,
) -> typing.Generator[EventFacade, None, None]:
    """Convert.

    Args:
        html (str): HTML representation of the events
        conference (ConferenceDetails): Details of the conference

    Yields:
        EventFacade: Event facade
    """
    bs = BeautifulSoup(html)

    tab = bs.find_all("div", class_="tab-content")
    tracks_and_days = tab[0].contents[0]

    first_day_checked = False
    track = None
    for entry in tracks_and_days:

        if entry["id"] == "tab_Track1":
            track = 1

        elif entry["id"] == "tab_Track2":
            track = 2

        else:
            break

        events_in_day_and_track = entry.find_all(
            "div",
            class_="schedule-listing",
        )

        for event in events_in_day_and_track:
            yield create_event_from_html(
                event,
                conference,
                conference.start_day + int(first_day_checked),
                track,
            )

        first_day_checked = not first_day_checked


def create_event_from_html(
    event: BeautifulSoup,
    conference: ConferenceDetails,
    day: int,
    track: int,
) -> EventFacade:
    """Convert HTML elements into a facade for an event.

    Args:
        event (BeautifulSoup): HTML representation of the event
        conference (ConferenceDetails): Details of the conference
        day (int): Day in which the event happens
        track (int): The ID on which the event happens

    Returns:
        EventFacade: Event facade
    """
    time = event.find_all("span", class_="schedule-slot-time")[0].contents[0]
    start_time, stop_time = time.split(" - ")
    start_time = convert_stringified_hour_to_utc(start_time)
    stop_time = convert_stringified_hour_to_utc(stop_time)
    title = event.find_all("h3", class_="schedule-slot-title")[0].contents[-1]
    speaker_find = event.find_all(
        "h4",
        class_="schedule-slot-speaker-name",
    )
    speaker = (
        (speaker_find[0].contents[0].contents[0]) if speaker_find else None
    )
    position = (
        speaker_find[0].contents[1].replace(" / ", "")
        if speaker_find
        else None
    )

    return EventFacade(
        conference,
        str(day),
        track,
        start_time,
        stop_time,
        title,
        speaker,
        position,
    )


def convert_stringified_hour_to_utc(date: str) -> str:
    """Convert a Romanian hour to the UTC correspondent.

    Args:
        date (str): String date

    Returns:
        str: String date, in UTC
    """
    date_pieces = date.split(":")

    return str(int(date_pieces[0]) - 2).zfill(2) + f":{date_pieces[1]}"


def create_calendar_from_event(
    events: typing.Iterable[EventFacade],
) -> Calendar:
    """Create an ICU calendar for from all event facade.

    Args:
        events (list[EventFacade]): List of events

    Returns:
        Calendar: ICS calendar
    """
    calendar = Calendar()
    for event in events:
        calendar.events.add(event.generate_ics_event())

    return calendar


def main() -> None:
    """Run the main functionality."""
    if len(sys.argv) != 5:
        print(
            f"Usage: {sys.argv[0]} EVENT_YEAR EVENT_MONTH EVENT_DAY"
            " EXPORT_FILE",
        )
        sys.exit(1)

    conference = ConferenceDetails(
        int(sys.argv[3]),
        int(sys.argv[2]),
        int(sys.argv[1]),
    )

    content = get_html()
    events = convert_html_to_events(content, conference)
    calendar = create_calendar_from_event(events)

    with open(sys.argv[4], "w") as f:
        f.writelines(calendar.serialize_iter())


if __name__ == "__main__":
    main()
