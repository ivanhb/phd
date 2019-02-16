#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2017, Silvio Peroni <essepuntato@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any purpose
# with or without fee is hereby granted, provided that the above copyright notice
# and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
# DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
# SOFTWARE.

# This script makes available a series of tools for calculating
# statistics related to the OpenCitations Corpus (access log,
# triples, social accounts).

import csv
import operator
import argparse
import json
import os
import requests
from time import sleep
import re

from rdflib import ConjunctiveGraph, URIRef
from rdflib.namespace import RDF

field_names = ['TIME', 'REMOTE_ADDR', 'HTTP_USER_AGENT', 'HTTP_REFERER', 'HTTP_HOST', 'REQUEST_URI']


def sum_column(file_log, header):
    print("Start sum_column")
    values = {}
    with open(file_log) as f:
        r = csv.DictReader(f, delimiter=',', quotechar='"')
        for row in r:
            cur_value = row[header]
            if cur_value not in values:
                values[cur_value] = 0
            values[cur_value] += + 1

    final_csv = []
    for key, value in sorted(values.items(), key=operator.itemgetter(1)):
        final_csv += [(key, value)]
        print(key, ":", value)

    print("End sum_column")
    return final_csv


def filter_out(file_log, no_list, columns=field_names):
    print("Start filter_out")

    final_csv = []

    with open(file_log) as f:
        r = csv.reader(f, delimiter=',', quotechar='"')
        for row in r:
            add_it = True
            for col in columns:
                cur_value = row[field_names.index(col)].lower()
                if not all([False if no_item in cur_value else True for no_item in no_list]):
                    add_it = False

            if add_it:
                final_csv += [row]

    print("End filter_out")
    return final_csv


def accesses(file_log, except_date):
    print("Start accesses")
    final_csv = []

    with open(file_log) as f:
        months = {}

        r = csv.reader(f, delimiter=',', quotechar='"')
        next(r)
        for row in r:
            cur_month = row[0][:7]
            if cur_month not in months:
                months[cur_month] = 0
            months[cur_month] += 1

        for key, value in sorted(months.items(), key=operator.itemgetter(0)):
            if key < except_date:
                final_csv += [(key, value)]

    final_csv.insert(0, ("month", "accesses"))

    print("End accesses")
    return final_csv


def statistics(file_log, except_date):
    print("Start statistics")
    final_csv = []

    with open(file_log) as f:
        pages = {}

        r = csv.reader(f, delimiter=',', quotechar='"')
        next(r)
        for row in r:
            cur_month = row[0][:7]
            cur_page = row[-1]
            cur_key = "/" + cur_page.split("/")[1].split(".")[0]
            if cur_key.startswith("/?"):
                cur_key = "/?"
            else:
                cur_key = re.sub("\?.*", "", cur_key)
            if cur_key not in pages:
                pages[cur_key] = []
            pages[cur_key] += [cur_month]

        month_page = {}
        for month in set(v for l in pages.values() for v in l):
            if month not in month_page:
                month_page[month] = {}
            for page in pages:
                month_page[month][page] = 0

        for page in pages:
            for month in pages[page]:
                month_page[month][page] += 1

        for month, page in month_page.items():
            month_page[month]["total"] = sum(page.values())

        for month, value in sorted(month_page.items(), key=operator.itemgetter(0)):
            if month < except_date:
                for page in value:
                    final_csv += [(month, page, value[page])]

        final_csv.insert(0, ("month", "page", "accesses"))

    print("End statistics")
    return final_csv


def countries(file_log, except_date, ip_country_path):
    print("Start countries")
    final_csv = []

    with open(file_log) as f:
        access_countries = {}

        ip_country = {}
        if os.path.exists(ip_country_path):
            with open(ip_country_path) as g:
                ip_country = json.load(g)

        finished_correctly = True
        r = csv.reader(f, delimiter=',', quotechar='"')
        next(r)
        for row in r:
            if row[0][:7] < except_date:
                cur_ip = row[1]
                try:
                    if cur_ip not in ip_country:
                        print("Check IP: %s" % cur_ip)
                        try:
                            response = requests.get("http://freegeoip.net/json/" + cur_ip, timeout=60)
                        except requests.exceptions.Timeout:
                            finished_correctly = False
                            break
                        source = response.text
                        j = json.loads(source)
                        country_code = j["country_code"]
                        if country_code == None or country_code == "":
                             country_code = "OTHER"
                        ip_country[cur_ip] = country_code
                        sleep(1)

                    cur_country = ip_country[cur_ip]
                    if cur_country not in access_countries:
                        access_countries[cur_country] = 0
                    access_countries[cur_country] += 1
                except Exception:
                    print("Exception IP:", cur_ip)

        for key, value in sorted(access_countries.items(), key=operator.itemgetter(1)):
            final_csv += [(key, value)]

        final_csv.insert(0, ("country", "accesses"))

    if not finished_correctly:
        print("Some IP was not processed due to timeout issues.")

    print("End countries")
    return final_csv, ip_country


def __load_jsonld(file_full_path, context_json):
    current_graph = ConjunctiveGraph()

    with open(file_full_path) as f:
        json_ld_file = json.load(f)
        if isinstance(json_ld_file, dict):
            json_ld_file = [json_ld_file]

        for json_ld_resource in json_ld_file:
            # Trick to force the use of a pre-loaded context if the format
            # specified is JSON-LD
            if "@context" in json_ld_resource:
                json_ld_resource["@context"] = context_json["@context"]

            current_graph.parse(data=json.dumps(json_ld_resource), format="json-ld")

    return current_graph


def top_ip(file_log, except_date, ip_country_path):
    result = {}

    with open(file_log) as f:
        ip_country = {}
        if os.path.exists(ip_country_path):
            with open(ip_country_path) as g:
                ip_country = json.load(g)

        r = csv.reader(f, delimiter=',', quotechar='"')
        next(r)
        for row in r:
            if row[0][:7] < except_date:
                cur_ip = row[1]
                if cur_ip not in result:
                    result[cur_ip] = 0
                result[cur_ip] += 1

        final_result = [("ip", "country", "accesses")]
        for ip, ac in sorted(result.items(), key=operator.itemgetter(1), reverse=True)[:20]:
            final_result.append((ip, ip_country[ip], ac))

    return final_result


# Things to eliminate in HTTP_USER_AGENT "crawler" "spider" "bot" "yahoo! slurp" "bubing"
#> -f "crawler" "spider" "bot" "yahoo! slurp" "bubing" -fc "HTTP_USER_AGENT"

# Excluding 127.0.0.1 from REMOTE_ADDR
#> -f "127.0.0.1" -fc "REMOTE_ADDR"

# Excluding oc.cs.unibo.it  HTTP_HOST
#> -f "oc.cs.unibo.it" -fc "HTTP_HOST"

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser("filter.py",
                                         description="Filter CSV of logs.")
    arg_parser.add_argument("-i", "--input", dest="input", required=True,
                            help="The file with logs in CSV.")
    arg_parser.add_argument("-o", "--output", dest="output",
                            help="The file where to store the data.")
    arg_parser.add_argument("-sc", "--sum_column", dest="sum_column", default=None,
                            help="Summarise the content of the column indicated.")
    arg_parser.add_argument("-f", "--filter_out", dest="filter_out", nargs="+",
                            help="Specify the row that should be filtered out by their content.")
    arg_parser.add_argument("-fc", "--filter_column", dest="filter_column", default=None,
                            help="Specify the column where to apply the filter.")
    arg_parser.add_argument("-a", "--accesses", dest="accesses", action="store_true", default=False,
                            help="Accesses to the website per month.")
    arg_parser.add_argument("-s", "--statistics", dest="statistics", action="store_true", default=False,
                            help="Statistics per page.")
    arg_parser.add_argument("-c", "--countries", dest="countries", action="store_true", default=False,
                            help="Countries that visited the website.")
    arg_parser.add_argument("-e", "--except_after", dest="except_after",
                            help="The date from which the data should not be considered (format yyyy-mm).")
    arg_parser.add_argument("-ip", "--ip_country", dest="ip_country",
                            help="The JSON containing the mapping between IP and countries.")
    arg_parser.add_argument("-tip", "--top_ip_visits", dest="top_ip_visits", action="store_true", default=False,
                            help="Check what are the IPs that did more visits to the website.")

    args = arg_parser.parse_args()
    final_result = None

    if args.except_after is None:
        except_date = "3000-01"
    else:
        except_date = args.except_after

    if args.ip_country is None:
        ip_country_path = os.path.dirname(args.output) + os.sep + "ip.json"
    else:
        ip_country_path = args.ip_country

    if args.sum_column is not None:
        final_result = sum_column(args.input, args.sum_column)
    elif args.filter_out is not None:
        final_result = filter_out(args.input, [fld.lower() for fld in args.filter_out], [args.filter_column])
    elif args.accesses:
        final_result = accesses(args.input, except_date)
    elif args.statistics:
        final_result = statistics(args.input, except_date)
    elif args.countries:
        final_result, ip_country = countries(args.input, except_date, ip_country_path)
        with open(ip_country_path, "w") as f:
            json.dump(ip_country, f)
    elif args.top_ip_visits and args.ip_country is not None:
        final_result = top_ip(args.input, except_date, ip_country_path)

    if args.output is not None and final_result is not None:
        with open(args.output, "w") as f:
            w = csv.writer(f)
            w.writerows(final_result)

    print("DONE")
