import csv
import re
import requests
import os
from datetime import datetime
import pandas as pd
import numpy as np
from collections import defaultdict
import pprint

def norm_isbn_code(x):
    regex = r"^([A-Z]{1,})\d"
    matches = re.finditer(regex, x, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        if match:
            return match.groups()[0]

def norm_pdftext(t):
    t = re.sub(r"(\w{1})\-\s(\w{1})", r"\1\2", t)
    return t

def norm_data(x):
    x = x.rstrip().lstrip()
    regex = r"(\d{4})"
    matches = re.finditer(regex, x, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        if match:
            return match.group()
    return "none"

def norm_source(x):
    x = x.rstrip().lstrip().lower()
    if x == "doi.org":
        return "doi"
    if x == "other":
        return "other"
    return "none"

def norm_title(x):
    x = x.rstrip().lstrip().lower()
    x = norm_pdftext(x)
    return x

def norm_abstract(x):
    x = x.rstrip().lstrip().lower()
    x = norm_pdftext(x)
    return x

def norm_section(x, intext_cits = None):
    x = x.rstrip().lstrip()
    sections = list(filter(None,[item for item in x.split(";;")]))
    sections = [item.split(";") for item in sections]
    for i,item_val in enumerate(sections):
        for p,part_val in enumerate(item_val):
            sections[i][p] = part_val.rstrip().lstrip().lower()
            if sections[i][p] == "none":
                return [["none"] for j in range(0,intext_cits)]
    return sections

def norm_cits_text(x):
    x = x.rstrip().lstrip()
    cits_text = [norm_pdftext(item.rstrip().lstrip().lower()) for item in x.split(";;")]
    cits_text = list(filter(None, cits_text))
    return cits_text

def norm_cit_intent(x):
    x = x.rstrip().lstrip()
    cit_intent = [item.rstrip().lstrip().lower() for item in x.split(";;")]
    cit_intent = list(filter(None, cit_intent))
    return cit_intent

def norm_sentiment(x):
    x = x.rstrip().lstrip()
    sentiment = [item.rstrip().lstrip().lower() for item in x.split(";;")]
    sentiment = list(filter(None, sentiment))
    return sentiment

def norm_retraction_men(x):
    x = x.rstrip().lstrip().lower()
    x = x.replace(";;","")
    return x

def norm_note(x):
    x = x.rstrip().lstrip()
    note = [item.rstrip().lstrip().lower() for item in x.split(";;")]
    note = list(filter(None, note))
    return note

## Normalize sources

def norm_area(x):
    x = x.rstrip().lstrip()
    norm_val = [item.rstrip().lstrip().lower() for item in x.split(";;")]
    norm_val = list(filter(None, norm_val))
    return norm_val

def norm_category(x):
    x = x.rstrip().lstrip()
    norm_val = list(filter(None,[item for item in x.split(";;")]))
    norm_val = [item.split(";") for item in norm_val]
    for i,item_val in enumerate(norm_val):
        for p,part_val in enumerate(item_val):
            norm_val[i][p] = part_val.rstrip().lstrip().lower()
    return norm_val

def norm_source_id(x):
    def filter_null(x):
        return x[0] != ""

    x = x.rstrip().lstrip()
    norm_val = [item.rstrip().lstrip().lower() for item in x.split(";")]
    norm_val = [tuple(item.split(":")) for item in norm_val]
    norm_val = list(filter(filter_null, norm_val))
    return norm_val

def norm_dois(x):
    x = x.rstrip().lstrip()
    norm_val = [item.rstrip().lstrip().lower() for item in x.split("[[;;]]")]
    norm_val = list(filter(None, norm_val))
    return norm_val
