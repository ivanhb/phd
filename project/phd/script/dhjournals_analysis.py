from argparse import ArgumentParser
from os.path import exists
from os import makedirs, sep
import csv
import requests
import json
import re

ERR_INDEX_FILE_EX1 = ".script_temp/djjournals_analysis_ex1_err.csv"
PROCESSED_INDEX = ".script_temp/djjournals_analysis_ex1_processed.csv"
RES_FILE_EX1 = "djjournals_analysis_ex1.csv"
INPUT_EX1_UPDATED = ""


def store(str_content, dest_file, is_header = False):
    if is_header:
        if exists(dest_file):
            return "Header is in already"
    with open(dest_file, "a") as g:
        g.write(str_content+"\n")

#Converts timespan values (in ISO_8601 Durations format) in a Total days number
def convert_timespan(str_timespan):
    timespan_parts = {
        "day": {"reg":"(\d{1,})D","val":1},
        "month": {"reg":"(\d{1,})M","val":30},
        "year": {"reg":"(\d{1,})Y","val":365}
    }

    totdays = 0
    for t_part in timespan_parts:
        t_elem = timespan_parts[t_part]
        val_part = re.findall(t_elem["reg"],str_timespan)
        if len(val_part) > 0:
            totdays = totdays + (int(val_part[0]) * t_elem["val"])

    return totdays

#takes an id and its related list of DOIs and calls COCI for each DOI in the list
def call_coci(id,dois_list):
    COCI_API_REFS = "https://opencitations.net/index/coci/api/v1/references/%s"

    tot_refs_list = []
    avg_timespan_list = []
    in_coci_with_ref = 0
    for a_doi in dois_list:
        response = requests.get(COCI_API_REFS%a_doi)
        if response.status_code == 200:
            json_res = json.loads(response.content)

            print("For DOI="+str(a_doi)+"  -> COCI got #"+str(len(json_res))+" references")
            tot_timespan = 0
            for a_ref in json_res:
                tot_timespan += convert_timespan(a_ref["timespan"])

            if len(json_res) > 0:
                in_coci_with_ref += 1
                tot_refs_list.append(len(json_res))
                avg_timespan_list.append(tot_timespan/len(json_res))
                print("  -> And an Average references age equal to:"+str(tot_timespan/len(json_res)))
            else:
                store('"'+str(id)+'","'+str(a_doi)+'"', INPUT_EX1_UPDATED)

        else:
            store('"'+str(id)+'","'+str(a_doi)+'","internal_server_error"', ERR_INDEX_FILE_EX1)

    avg_refs_timespan = "-1"
    if len(avg_timespan_list) > 0:
        avg_refs_timespan = str(int(sum(avg_timespan_list) / len(avg_timespan_list)))

    print("Avg Refs timespan of: "+id+"  equals:"+avg_refs_timespan)

    avg_refs_x_doi = "-1"
    if len(avg_timespan_list) > 0:
        avg_refs_x_doi = str(int(sum(tot_refs_list) / in_coci_with_ref))

    store('"'
        +str(id)+'","'
        +str(in_coci_with_ref)+'","'
        +avg_refs_x_doi+'","'
        +avg_refs_timespan+
        '"', RES_FILE_EX1)

if __name__ == "__main__":
    arg_parser = ArgumentParser("dhjournals_analysis.py", description="Do some analysis on the DH journals data")
    arg_parser.add_argument("-in", "--input", dest="dh_dois_file", required=True, help="The csv file (full path) of the DOIs")
    arg_parser.add_argument("-out", "--output", dest="output_dir", required=False, help="The output directory where the results will be stored")
    arg_parser.add_argument("-coci", "--coci", dest="coci", action='store_true', required=False, help="Call COCI")

    args = arg_parser.parse_args()

    csv_reader = csv.reader(open(args.dh_dois_file), delimiter=',')
    next(csv_reader)

    #EX1: make analysis on the DOIs
    index_to_insert = args.dh_dois_file.find('.csv')
    INPUT_EX1_UPDATED = args.dh_dois_file[:index_to_insert] + '_notin_coci' + args.dh_dois_file[index_to_insert:]

    if exists(args.output_dir):
        RES_FILE_EX1 = args.output_dir+RES_FILE_EX1

    store("id,doi", INPUT_EX1_UPDATED, True)
    store("id,dois_in_coci_with_refs,avg_refs_x_doi,avg_refs_timespan", RES_FILE_EX1, True)
    store("id,elem,value", ERR_INDEX_FILE_EX1, True)
    store("id", PROCESSED_INDEX, True)

    #reload processed elements
    index_processed = {}
    csv_reader_processed = csv.reader(open(PROCESSED_INDEX), delimiter=',')
    next(csv_reader_processed)
    for row in csv_reader_processed:
        index_processed[row[0]] = True

    #now start processing
    index = {}
    for row in csv_reader:
        if row[0] not in index_processed:
            if row[0] in index:
                index[row[0]].append(row[1])
            else:
                #a new id to elaborate
                index[row[0]] = []
                all_keys = list(index.keys())

                #take the previous elements set of a specific <id>, and process them
                if len(all_keys) > 1:
                    id_val = all_keys[-2]
                    dois_list = index[all_keys[-2]]

                    if args.coci:
                        print("Do the analysis with COCI dataset")
                        call_coci(id_val,dois_list)
                        store('"'+str(id_val)+'"', PROCESSED_INDEX)
                        break
