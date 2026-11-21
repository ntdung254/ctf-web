#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Respect the shebang and mark file as executable

import random
import flask
from flask import Flask
from flask import render_template
from waitress import serve

# create and configure the app
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY=random.randbytes(128)
)

LOSTEAMS = [
    "LosFuzzys", "S1gW0zzys", "podmanenjoyer"
]

AT_TEAMS = [
    # The OGs wouldn't do it
    "WE_0WN_Y0U", "HgbSec", "KuK Hofhackerei", "SIGFLAG", "/dev/stp",
    "OneManParty", "defragmented brains", "WeAreScientists"

    # These ones are also not known for using AI
    "sp3ng3rh4ck", "GiG Gehackt ist Geil", "inFLAGranti",
    "MeetingPostponed", "KUDDAHSEC", "Zook"
]


@app.route('/index.html')
@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(404)
def error_handler():
    return flask.redirect("index")


@app.route('/check_team')
def challenge():
    team_name = flask.request.args.get("teamname")
    if not team_name:
        return render_template('index.html')

    # Security-Checks
    if "{{" in team_name or "}}" in team_name:
        return render_template('index.html')

    team_msg = flask.render_template_string(
        f"We are unsure if {team_name} has used AI in the past."
    )
    info_color = "info"

    if team_name in AT_TEAMS:
        team_msg = f"We don't think that {team_name} has used AI in the past"
        info_color = "success"

    elif team_name in LOSTEAMS:
        team_msg = f"Yes, {team_name} has has used AI in the past!"
        info_color = "danger"

    return render_template(
        'index.html', team_msg=team_msg, info_color=info_color
    )


serve(app, host='0.0.0.0', port=1337)
