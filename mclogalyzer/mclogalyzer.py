#!/usr/bin/env python2

# Copyright 2013-2015 Moritz Hilscher
#
#  This file is part of mclogalyzer.
#
#  mclogalyzer is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  mclogalyzer is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with mclogalyzer.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import datetime
import gzip
import json
import os
import re
import sys
import time

import jinja2


REGEX_IP = "(\d+)\.(\d+)\.(\d+)\.(\d+)"

REGEX_LOGIN_USERNAME = re.compile("\[Server thread\/INFO\]: ([^]]+)\[")
REGEX_LOGOUT_USERNAME = re.compile("\[Server thread\/INFO\]: ([^ ]+) lost connection")
REGEX_LOGOUT_USERNAME2 = re.compile(
    "\[Server thread\/INFO\]:.*GameProfile.*name='?([^ ,']+)'?.* lost connection")
REGEX_KICK_USERNAME = re.compile("\[INFO\] CONSOLE: Kicked player ([^ ]*)")
REGEX_ACHIEVEMENT = re.compile("\[Server thread\/INFO\]: ([^ ]+) has just earned the achievement \[(.*)\]")

# regular expression to get the username of a chat message
# you need to change this if you have special chat prefixes or stuff like that
# this regex works with chat messages of the format: <prefix username> chat message
REGEX_CHAT_USERNAME = re.compile("\[Server thread\/INFO\]: <([^>]* )?([^ ]*)>")

DEATH_MESSAGES = (
    "was squashed by.*",
    "was pricked to death",
    "walked into a cactus whilst trying to escape.*",
    "drowned.*",
    "blew up",
    "was blown up by.*",
    "fell from a high place.*",
    "hit the ground too hard",
    "fell off a ladder",
    "fell off some vines",
    "fell out of the water",
    "fell into a patch of.*",
    "was doomed to fall.*",
    "was shot off.*",
    "was blown from a high place.*",
    "went up in flames",
    "burned to death",
    "was burnt to a crisp whilst fighting.*",
    "walked into a fire whilst fighting.*",
    "was slain by.*",
    "was shot by.*",
    "was fireballed by.*",
    "was killed.*",
    "got finished off by.*",
    "tried to swim in lava.*",
    "died",
    "was struck by lighting",
    "starved to death",
    "suffocated in a wall",
    "was pummeled by.*",
    "fell out of the world",
    "was knocked into the void.*",
    "withered away",
)

REGEX_DEATH_MESSAGES = set()
for message in DEATH_MESSAGES:
    REGEX_DEATH_MESSAGES.add(re.compile("\Server thread\/INFO\]: ([^ ]+) (" + message + ")"))

# Will have to update this when number of achievements change.
# Got this value from http://minecraft.gamepedia.com/Achievements
ACHIEVEMENTS_AVAILABLE = 34

def capitalize_first(str):
    if not len(str):
        return ""
    return str[:1].upper() + str[1:]


class UserStats:
    def __init__(self, username=""):
        self._username = username
        self._logins = 0

        self._active_days = set()
        self._prev_login = None
        self._first_login = None
        self._last_login = None
        self._time = datetime.timedelta()
        self._longest_session = datetime.timedelta()

        self._death_count = 0
        self._death_types = {}

        self._messages = 0

        self._achievement_count = 0
        self._achievements = []

    def handle_logout(self, date):
        if self._prev_login is None:
            return
        session = date - self._prev_login
        self._time += session
        self._longest_session = max(self._longest_session, session)
        self._prev_login = None

    @property
    def username(self):
        return self._username

    @property
    def logins(self):
        return self._logins

    @property
    def time(self):
        return format_delta(self._time)

    @property
    def time_per_login(self):
        return format_delta(
            self._time / self._logins if self._logins != 0 else datetime.timedelta(), False)

    @property
    def active_days(self):
        return len(self._active_days)

    @property
    def time_per_active_day(self):
        return format_delta(
            self._time / self.active_days if self.active_days != 0 else datetime.timedelta(), False)

    @property
    def first_login(self):
        return str(self._first_login)

    @property
    def last_login(self):
        return str(self._last_login)

    @property
    def longest_session(self):
        return format_delta(self._longest_session, False)

    @property
    def messages(self):
        return self._messages

    @property
    def time_per_message(self):
        if self._messages == 0:
            return "<div class='text-center'>-</div>"
        return format_delta(
            self._time / self._messages if self._messages != 0 else datetime.timedelta())

    @property
    def death_count(self):
        return self._death_count

    @property
    def death_types(self):
        return sorted(self._death_types.items(), key=lambda k: k[1])

    @property
    def achievement_count(self):
        return self._achievement_count

    @property
    def achievements(self):
        return sorted(self._achievements)

class ServerStats:
    def __init__(self):
        self._statistics_since = None
        self._time_played = datetime.timedelta()
        self._max_players = 0
        self._max_players_date = None

    @property
    def statistics_since(self):
        return self._statistics_since

    @property
    def time_played(self):
        return format_delta(self._time_played, True, True)

    @property
    def max_players(self):
        return self._max_players

    @property
    def max_players_date(self):
        return self._max_players_date


def grep_logname_date(line):
    try:
        d = time.strptime("-".join(line.split("-")[:3]), "%Y-%m-%d")
    except ValueError:
        return None
    return datetime.date(*(d[0:3]))


def grep_log_datetime(date, line):
    try:
        d = time.strptime(line.split(" ")[0], "[%H:%M:%S]")
    except ValueError:
        return None
    return datetime.datetime(
        year=date.year, month=date.month, day=date.day,
        hour=d.tm_hour, minute=d.tm_min, second=d.tm_sec
    )


def grep_login_username(line):
    search = REGEX_LOGIN_USERNAME.search(line)
    if not search:
        print "### Warning: Unable to find login username:", line
        return ""
    username = search.group(1).lstrip().rstrip()
    return username.decode("ascii", "ignore").encode("ascii", "ignore")


def grep_logout_username(line):
    search = REGEX_LOGOUT_USERNAME.search(line)
    if not search:
        search = REGEX_LOGOUT_USERNAME2.search(line)
        if not search:
            print "### Warning: Unable to find username:", line
            return ""
    username = search.group(1).lstrip().rstrip()
    return username.decode("ascii", "ignore").encode("ascii", "ignore")


def grep_kick_username(line):
    search = REGEX_KICK_USERNAME.search(line)
    if not search:
        print "### Warning: Unable to find kick logout username:", line
        return ""
    return search.group(1)[:-1].decode("ascii", "ignore").encode("ascii", "ignore")


def grep_death(line):
    for regex in REGEX_DEATH_MESSAGES:
        search = regex.search(line)
        if search:
            return search.group(1), capitalize_first(search.group(2))
    return None, None


def grep_achievement(line):
    search = REGEX_ACHIEVEMENT.search(line)
    if not search:
        print "### Warning: Unable to find achievement username or achievement:", line
        return None, None
    username = search.group(1)
    return username.decode("ascii", "ignore").encode("ascii", "ignore"), search.group(2)


def format_delta(timedelta, days=True, maybe_years=False):
    seconds = timedelta.seconds
    hours = seconds // 3600
    seconds = seconds - (hours * 3600)
    minutes = seconds // 60
    seconds = seconds - (minutes * 60)
    fmt = "%02dh %02dm %02ds" % (hours, minutes, seconds)
    if days:
        if maybe_years:
            days = timedelta.days
            years = days // 365
            days = days - (years * 365)
            if years > 0:
                return ("%d years, %02d days" % (years, days)) + fmt
        return ("%02d days, " % (timedelta.days)) + fmt
    return fmt


def parse_whitelist(whitelist_path):
    json_data = json.load(open(whitelist_path))
    return map(lambda x: x["name"], json_data)


def parse_logs(logdir, since=None, whitelist_users=None):
    users = {}
    server = ServerStats()
    online_players = set()

    first_date = None
    for logname in sorted(os.listdir(logdir)):
        if not re.match("\d{4}-\d{2}-\d{2}-\d+\.log\.gz", logname):
            continue

        today = grep_logname_date(logname)
        if first_date is None:
            first_date = today
        print "Parsing log %s (%s) ..." % (logname, today)

        logfile = gzip.open(os.path.join(logdir, logname))

        for line in logfile:
            line = line.rstrip()

            if "logged in with entity id" in line:
                date = grep_log_datetime(today, line)
                if date is None or (since is not None and date < since):
                    continue

                username = grep_login_username(line)
                if not username:
                    continue

                if whitelist_users is None or username in whitelist_users:
                    if username not in users:
                        users[username] = UserStats(username)
                    user = users[username]
                    user._active_days.add((date.year, date.month, date.day))
                    user._logins += 1
                    user._last_login = user._prev_login = date
                    if user._first_login is None:
                        user._first_login = date

                    online_players.add(username)
                    if len(online_players) > server._max_players:
                        server._max_players = len(online_players)
                        server._max_players_date = date

            elif "lost connection" in line or "[INFO] CONSOLE: Kicked player" in line:
                date = grep_log_datetime(today, line)
                if date is None or (since is not None and date < since):
                    continue

                username = ""
                if "lost connection" in line:
                    username = grep_logout_username(line)
                else:
                    username = grep_kick_username(line)

                if not username or username.startswith("/"):
                    continue
                if username not in users:
                    continue

                user = users[username]
                user._active_days.add((date.year, date.month, date.day))
                user.handle_logout(date)
                if username in online_players:
                    online_players.remove(username)

            elif "[INFO] Stopping server" in line:
                date = grep_log_datetime(today, line)
                if date is None or (since is not None and date < since):
                    continue

                for user in users.values():
                    user.handle_logout(date)
                online_players = set()

            elif "earned the achievement" in line:
                achievement_username, achievement = grep_achievement(line)
                if achievement_username is not None:
                    if achievement_username in users:
                        achievement_user = users[achievement_username]
                        achievement_user._achievement_count += 1
                        achievement_user._achievements.append(achievement)
            else:
                death_username, death_type = grep_death(line)
                if death_username is not None:
                    if death_username in users:
                        death_user = users[death_username]
                        death_user._death_count += 1
                        if death_type not in death_user._death_types:
                            death_user._death_types[death_type] = 0
                        death_user._death_types[death_type] += 1
                else:
                    search = REGEX_CHAT_USERNAME.search(line)
                    if not search:
                        continue
                    username = search.group(2)
                    if username in users:
                        users[username]._messages += 1

    if whitelist_users is not None:
        for username in whitelist_users:
            if username not in users:
                users[username] = UserStats(username)

    users = users.values()
    users.sort(key=lambda user: user.time, reverse=True)

    server._statistics_since = since if since is not None else first_date
    for user in users:
        server._time_played += user._time

    return users, server


def main():
    parser = argparse.ArgumentParser(
        description="Analyzes the Minecraft Server Log files and generates some statistics.")
    parser.add_argument("-t", "--template",
                        help="the template to generate the output file",
                        metavar="template")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--since",
                       help="ignores the log before this date, must be in format year-month-day hour:minute:second",
                       metavar="<datetime>")
    group.add_argument("--month",
                       action='store_true', help="create report of last month")
    group.add_argument("--week",
                       action='store_true', help="create report of last week")
    parser.add_argument("-w", "--whitelist",
                        help="the whitelist of the server (only use included usernames)",
                        metavar="<whitelist>")
    parser.add_argument("logdir",
                        help="the server log directory",
                        metavar="<logdir>")
    parser.add_argument("output",
                        help="the output html file",
                        metavar="<outputfile>")
    args = vars(parser.parse_args())

    since = None
    if args['month']:
        since = datetime.datetime.now() - datetime.timedelta(days=30)
    elif args['week']:
        since = datetime.datetime.now() - datetime.timedelta(days=7)
    elif args["since"] is not None:
        try:
            d = time.strptime(args["since"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print "Invalid datetime format! The format must be year-month-day hour:minute:second ."
            sys.exit(1)
        since = datetime.datetime(*(d[0:6]))

    whitelist_users = parse_whitelist(args["whitelist"]) if args["whitelist"] else None
    users, server = parse_logs(args["logdir"], since, whitelist_users)

    template_path = os.path.join(os.path.dirname(__file__), "template.html")
    if args["template"] is not None:
        template_path = args["template"]
    template_dir = os.path.dirname(template_path)
    template_name = os.path.basename(template_path)
    #print template_path
    #print template_dir, template_name
    if not os.path.exists(template_path):
        print "Unable to find template file %s!" % template_path
        sys.exit(1)

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    template = env.get_template(template_name)

    f = open(args["output"], "w")
    f.write(template.render(users=users,
                            server=server,
                            achievements_available=ACHIEVEMENTS_AVAILABLE,
                            last_update=time.strftime("%Y-%m-%d %H:%M:%S")))
    f.close()


if __name__ == "__main__":
    main()
