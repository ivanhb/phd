from argparse import ArgumentParser
from os.path import exists
from os import makedirs, sep
import csv
import requests
import json
import re

#Index files used during the elaboration
ERR_INDEX_FILE = ".script_temp/analysis_%s_err.csv"
PROCESSED_INDEX_FILE = ".script_temp/analysis_%s_processed.csv"
#The results of the experiments made
RESULTS_FILE = "analysis_%s_res.csv"
EXTRA_RESULTS = ""

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
def do_ex1(id,dois_list):
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
                store('"'+str(id)+'","'+str(a_doi)+'"', EXTRA_RESULTS)

        else:
            store('"'+str(id)+'","'+str(a_doi)+'","internal_server_error"', ERR_INDEX_FILE)

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
        '"', RESULTS_FILE)

if __name__ == "__main__":
    arg_parser = ArgumentParser("dhjournals_analysis.py", description="Do some analysis on the DH journals data")
    arg_parser.add_argument("-ex", "--experiment", dest="ex_val", required=True, help="The experiment number")
    arg_parser.add_argument("-in", "--input", dest="dh_dois_file", required=True, help="The csv file (full path) of the DOIs")
    arg_parser.add_argument("-out", "--output", dest="output_dir", required=False, help="The output directory where the results will be stored")
    args = arg_parser.parse_args()

    ## Pre processing phase common operations: for all the experiments
    ## ----------------------------
    # 0) Define the FILES and PATHS
    ERR_INDEX_FILE = ERR_INDEX_FILE%args.ex_val
    PROCESSED_INDEX_FILE = PROCESSED_INDEX_FILE%args.ex_val
    RESULTS_FILE = RESULTS_FILE%args.ex_val
    if exists(args.output_dir):
        RESULTS_FILE = args.output_dir+RESULTS_FILE
    ## -----
    # 1) Define the Indexs files
    store("id,elem,value", ERR_INDEX_FILE, True)
    store("id", PROCESSED_INDEX_FILE, True)
    ## -----
    # 2) reload processed elements
    index_processed = {}
    csv_reader_processed = csv.reader(open(PROCESSED_INDEX_FILE), delimiter=',')
    next(csv_reader_processed)
    for row in csv_reader_processed:
        index_processed[row[0]] = True


    ## Processing Phase
    ## ----------------------------
    index = {}
    csv_reader = csv.reader(open(args.dh_dois_file), delimiter=',')
    next(csv_reader)
    for row in csv_reader:
        if row[0] not in index_processed:
            ## -----
            # Check the experiment value

            # Experiment 1
            ## -----
            if args.ex_val == "1":
                #EX1 Definitions: make analysis on the DOIs
                store("id,dois_in_coci_with_refs,avg_refs_x_doi,avg_refs_timespan", RESULTS_FILE, True)
                EXTRA_RESULTS = 'dois_notin_coci.csv'
                if exists(args.output_dir):
                    EXTRA_RESULTS = args.output_dir+EXTRA_RESULTS
                store("id,doi", EXTRA_RESULTS, True)

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
                        print("Do the analysis with COCI dataset")
                        do_ex1(id_val,dois_list)
                        store('"'+str(id_val)+'"', PROCESSED_INDEX_FILE)

            # Experiment 2
            ## -----
            if args.ex_val == "2":
                #EX2 Definitions: make analysis on the DOIs
                break
