from argparse import ArgumentParser
from os.path import exists
from os import makedirs, sep
import csv
import requests
import json
import re
import time


#Index files used during the elaboration
ERR_INDEX_FILE = ".script_temp/analysis_%s_err.csv"
PROCESSED_INDEX_FILE = ".script_temp/analysis_%s_processed.csv"
#The results of the experiments made
RESULTS_FILE = "analysis_res"
EXTRA_RESULTS = ""

def progress_bar(current_val, final_val, prefix= ""):
    print(str(prefix)+str(round((current_val/final_val)*100)),end=" percent complete         \r")

def store(str_content, dest_file, is_header = False):
    if is_header:
        if exists(dest_file):
            return "Header is in already"
    with open(dest_file, "a") as g:
        g.write(str_content+"\n")

def store_json(data, dest_file):
    with open(dest_file, 'w') as outfile:
        json.dump(data, outfile)


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

#Get all the crossref data for all the DOIs in the journal dois dataset
def do_ex3(id, a_j_path):

    CROSSREF_API_DOI = "https://api.crossref.org/works/%s"

    json_file = open(a_j_path)
    list_data = json.load(json_file)

    tot_count = len(list_data)
    ref_list = []
    doi_refs_list = []
    nondoi_refs_list = []
    nondoi_json_data = []
    doi_json_data = []
    prog_count = 1
    for a_obj in list_data:
        if "reference" in a_obj["message"]:
            obj_refs = a_obj["message"]["reference"]
            ref_list.append(len(obj_refs))
            ref_with_doi = 0
            ref_prog_count = 0
            for a_ref in obj_refs:
                progress_bar(prog_count, len(list_data), " Processing reference num: "+str(ref_prog_count)+"; Of element number: "+str(prog_count)+"; ")
                ref_prog_count += 1

                if "DOI" in a_ref:
                    ref_with_doi += 1
                    for try_i in range(0,5):
                        response = requests.get(CROSSREF_API_DOI%a_ref["DOI"])
                        if response.status_code == 200:
                            doi_json_data.append(json.loads(response.content))
                            break
                        else:
                            time.sleep(5*try_i)

                        if try_i == 4:
                            store('"'+str(id)+'","'+str(a_ref["DOI"])+'","internal_server_error"', ERR_INDEX_FILE)

                else:
                    nondoi_json_data.append(a_ref)

            doi_refs_list.append(ref_with_doi)
            nondoi_refs_list.append(len(obj_refs) - ref_with_doi)

        prog_count += 1

    avg_ref = -1
    count_with_ref = len(ref_list)
    if count_with_ref > 0:
        avg_ref = sum(ref_list)/count_with_ref

    avg_doi_refs = -1
    count = len(doi_refs_list)
    if count > 0:
        avg_doi_refs = sum(doi_refs_list)/count

    avg_nondoi_refs = -1
    count = len(nondoi_refs_list)
    if count > 0:
        avg_nondoi_refs = sum(nondoi_refs_list)/count

    store_json(nondoi_json_data, RESULTS_FILE+"_"+str(id)+"_nondoirefs.json")
    store_json(doi_json_data, RESULTS_FILE+"_"+str(id)+"_doirefs.json")
    store("id,dois_in_cr,dois_in_cr_with_refs,avg_refs_x_elem,avg_doirefs_x_elem,avg_non_doirefs_x_elem", RESULTS_FILE+".csv", True)
    store('"'
        +str(id)+'","'
        +str(len(list_data))+'","'
        +str(count_with_ref)+'","'
        +str(round(avg_ref,2))+'","'
        +str(round(avg_doi_refs,2))+'","'
        +str(round(avg_nondoi_refs,2))+
        '"', RESULTS_FILE+".csv")


    print(str(i)+": #with refs: "+str(count_with_ref)+
          ";\n   out of: "+ str(len(list_data))+
          ";\n   average ref: "+str(round(avg_ref,2))+
          ";\n   average DOI refs: "+str(round(avg_doi_refs,2))+
          ";\n   average non-DOI refs: "+str(round(avg_nondoi_refs,2))+
          "\n"
    )

#Get a backup of all the DOI item in Crossref
#the generated file will have the id value and a list of all its items
def do_ex2(id,dois_list):
    CROSSREF_API_DOI = "https://api.crossref.org/works/%s"
    json_data = []

    count = 1
    for a_doi in dois_list:
        response = requests.get(CROSSREF_API_DOI%a_doi)
        if response.status_code == 200:
            json_data.append(json.loads(response.content))

        progress_bar(count, len(dois_list))
        count += 1

    store_json(json_data, RESULTS_FILE+"_"+str(id)+".json")
    return json_data



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
    arg_parser.add_argument("-in", "--input", dest="arg_input", required=True, help="The csv file (full path) of the DOIs")
    arg_parser.add_argument("-out", "--output", dest="output_dir", required=False, help="The output directory where the results will be stored")
    args = arg_parser.parse_args()

    ## Pre processing phase common operations: for all the experiments
    ## ----------------------------
    # 0) Define the FILES and PATHS
    ERR_INDEX_FILE = ERR_INDEX_FILE%args.ex_val
    PROCESSED_INDEX_FILE = PROCESSED_INDEX_FILE%args.ex_val
    RESULTS_FILE = RESULTS_FILE+"_ex"+str(args.ex_val)
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
    INIT_BOOL = True

    if ((args.ex_val == "1") or (args.ex_val == "2")) :
        data_to_process = csv.reader(open(args.arg_input), delimiter=',')
        next(data_to_process)
        for row in data_to_process:
            if row[0] not in index_processed:
                ## -----
                # Check the experiment value

                # Experiment 1
                ## -----
                if args.ex_val == "1":
                    if INIT_BOOL:
                        RESULTS_FILE = RESULTS_FILE+".csv"
                        #EX1 Definitions: make analysis on the DOIs
                        store("id,dois_in_coci_with_refs,avg_refs_x_doi,avg_refs_timespan", RESULTS_FILE, INIT_BOOL)
                        EXTRA_RESULTS = 'dois_notin_coci.csv'
                        if exists(args.output_dir):
                            EXTRA_RESULTS = args.output_dir+EXTRA_RESULTS
                        store("id,doi", EXTRA_RESULTS, INIT_BOOL)
                        INIT_BOOL = False

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
                    if row[0] in index:
                        index[row[0]].append(row[1])
                    else:
                        #a new id to elaborate
                        index[row[0]] = []
                        all_keys = list(index.keys())
                        if len(all_keys) > 1:
                            id_val = all_keys[-2]
                            dois_list = index[all_keys[-2]]
                            print("Download all CROSSREF data for journal id="+str(id_val))
                            do_ex2(id_val,dois_list)
                            store('"'+str(id_val)+'"', PROCESSED_INDEX_FILE)

    # Experiment 3
    ## -----
    elif args.ex_val == "3":
        cr_journal_data_path = args.arg_input+"analysis_res_ex2_%s.json"
        for i in range(0,100):
            if i not in index_processed:
                a_j_path = cr_journal_data_path%i
                if exists(a_j_path):
                    do_ex3(i, a_j_path)
                    store('"'+str(i)+'"', PROCESSED_INDEX_FILE)


    #Last id to process
    ## -----
    if args.ex_val == "1":
        id_val = list(index.keys())[-1]
        do_ex1(id_val,index[id_val])

    if args.ex_val == "2":
        id_val = list(index.keys())[-1]
        do_ex2(id_val,index[id_val])
